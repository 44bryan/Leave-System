"""
Generate a professional Leave Authorisation PDF for
Magrabi Cameroon Eye Institute — LeaveDesk HR System.

Design: entire document in Magrabi logo color family (cyan / blue),
        label/value cells, 2×2 approval grid with embedded signatures.
"""
from io import BytesIO
from datetime import timedelta, date as _date
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit, ImageReader


# ── colour palette — ALL derived from logo #31b8cf = rgb(49,184,207), hue 189° ─
# Each shade is a blend of the logo color toward black (dark) or white (light),
# ensuring one uniform hue throughout the whole document.
_HDR_BG  = (0.086, 0.325, 0.365)   # #16535d  logo→black 55%  — section bars (white text)
_CYAN    = (0.192, 0.722, 0.812)   # #31b8cf  logo 100%        — approval cell headers
_BLUE    = (0.114, 0.431, 0.486)   # #1d6e7c  logo→black 40%   — subtitle, accents
_DARK    = (0.027, 0.110, 0.122)   # #071c1f  logo→black 85%   — near-black body text
_LABEL   = (0.114, 0.431, 0.486)   # #1d6e7c  logo→black 40%   — field labels
_BORDER  = (0.314, 0.769, 0.851)   # #50c4d9  logo→white 10%   — cell outlines
_CELL_BG = (0.878, 0.957, 0.973)   # #e0f4f8  logo→white 85%   — cell background
_ALT_BG  = (0.757, 0.918, 0.945)   # #c1eaf1  logo→white 70%   — alternating rows
_PAGE_BG = (0.945, 0.980, 0.988)   # #f1fafc  logo→white 93%   — page background wash
_WHITE   = (1.0,   1.0,   1.0  )


# ── helpers ───────────────────────────────────────────────────────────────────

def _d(d):
    """Format date/datetime → DD/MM/YYYY or '—'."""
    if d is None:
        return "—"
    if hasattr(d, "date"):
        d = d.date()
    return d.strftime("%d/%m/%Y")


def _resume(end_date):
    """First working day (skip Sunday) after end_date."""
    d = end_date + timedelta(days=1)
    while d.weekday() == 6:
        d += timedelta(days=1)
    return d


def _load_sig(employee_obj):
    """
    Return a ReportLab ImageReader for the employee's signature PNG, or None.
    Composites transparent/RGBA images onto white so mask=None works correctly.
    """
    if not employee_obj:
        return None
    try:
        sig = employee_obj.signature
    except Exception:
        return None
    if not sig:
        return None

    try:
        from PIL import Image as PILImage
        import io as _io

        # Try .path first (local filesystem), fall back to .open() (cloud/Railway)
        try:
            pil_img = PILImage.open(sig.path)
        except Exception:
            try:
                with sig.open('rb') as fh:
                    raw_bytes = fh.read()
                pil_img = PILImage.open(_io.BytesIO(raw_bytes))
            except Exception:
                return None

        pil_img.load()

        # Flatten any transparency onto white so we get a clean RGB image
        if pil_img.mode in ('RGBA', 'LA', 'P'):
            rgba = pil_img.convert('RGBA')
            bg = PILImage.new('RGBA', rgba.size, (255, 255, 255, 255))
            bg.paste(rgba, mask=rgba.split()[3])
            pil_img = bg.convert('RGB')
        else:
            pil_img = pil_img.convert('RGB')

        out = _io.BytesIO()
        pil_img.save(out, format='PNG')
        out.seek(0)
        return ImageReader(out)

    except Exception:
        return None


# ── main generator ────────────────────────────────────────────────────────────

def generate_leave_pdf(leave):
    buf = BytesIO()
    cv  = canvas.Canvas(buf, pagesize=A4)
    W, H = A4   # 595.28 × 841.89 pt

    emp  = leave.employee
    year = leave.start_date.year

    try:
        bal        = emp.leave_balances.get(year=year)
        avail_days = str(bal.total_available)
    except Exception:
        avail_days = "—"

    LM = 15 * mm
    RM = W - 15 * mm
    CW = RM - LM        # ≈ 165 mm

    # ── drawing primitives ────────────────────────────────────────────────────

    def frect(x, y_top, w, h, fill, stroke=None, sw=0.5):
        """Filled rectangle; y_top = top edge."""
        cv.setLineWidth(sw)
        cv.setFillColorRGB(*fill)
        if stroke:
            cv.setStrokeColorRGB(*stroke)
            cv.rect(x, y_top - h, w, h, fill=1, stroke=1)
        else:
            cv.rect(x, y_top - h, w, h, fill=1, stroke=0)

    def txt(s, x, y, font="Helvetica", size=9, rgb=_DARK):
        cv.setFillColorRGB(*rgb)
        cv.setFont(font, size)
        cv.drawString(x, y, str(s))

    def section_bar(y_top, label):
        """Dark-teal section header bar. Returns new y (below bar)."""
        h = 7 * mm
        frect(LM, y_top, CW, h, _HDR_BG)
        cv.setFillColorRGB(*_WHITE)
        cv.setFont("Helvetica-Bold", 8.5)
        cv.drawString(LM + 4*mm, y_top - h + 2.2*mm, label)
        return y_top - h

    def info_row(y_top, pairs, row_h=12*mm, alt=False):
        """
        One data row split into N equal cells.
        Each cell: label (blue-teal, small) above value (bold dark).
        """
        n  = len(pairs)
        cw = CW / n
        bg = _ALT_BG if alt else _CELL_BG
        for i, (lbl, val) in enumerate(pairs):
            x = LM + i * cw
            frect(x, y_top, cw, row_h, bg, _BORDER, 0.5)
            txt(lbl,          x + 3*mm, y_top - 4*mm,   "Helvetica",      7,   _LABEL)
            txt(val or "—",   x + 3*mm, y_top - 9.5*mm, "Helvetica-Bold", 9.5, _DARK)
        return y_top - row_h

    def draw_sig(emp_obj, x, y_top, max_w, max_h):
        """
        Draw signature image within the bounding box.
        mask=None because PIL already composited the image to RGB (no alpha).
        Returns True if drawn.
        """
        reader = _load_sig(emp_obj)
        if reader is None:
            return False
        try:
            cv.drawImage(
                reader, x, y_top - max_h,
                width=max_w, height=max_h,
                preserveAspectRatio=True,
                mask=None,
            )
            return True
        except Exception:
            return False

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE BACKGROUND WASH — subtle cyan tint over the whole page
    # ══════════════════════════════════════════════════════════════════════════
    frect(0, H, W, H, _PAGE_BG)

    # ══════════════════════════════════════════════════════════════════════════
    # TOP ACCENT BAR
    # ══════════════════════════════════════════════════════════════════════════
    frect(0, H, W, 8*mm, _HDR_BG)

    # ══════════════════════════════════════════════════════════════════════════
    # HEADER  (logo left · title centre · ref top-right)
    # ══════════════════════════════════════════════════════════════════════════
    HDR_TOP = H - 8*mm
    HDR_H   = 28*mm

    logo_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "static", "LOGO.png"
    )
    if os.path.exists(logo_path):
        cv.drawImage(logo_path, LM, HDR_TOP - HDR_H + 4*mm,
                     width=55*mm, height=22*mm,
                     preserveAspectRatio=True, mask='auto')

    title_cx = LM + 55*mm + (CW - 55*mm) / 2
    cv.setFillColorRGB(*_HDR_BG)
    cv.setFont("Helvetica-Bold", 13)
    cv.drawCentredString(title_cx, HDR_TOP - 13*mm, "AUTORISATION D'ABSENCE")
    cv.setFillColorRGB(*_BLUE)
    cv.setFont("Helvetica", 10)
    cv.drawCentredString(title_cx, HDR_TOP - 20*mm, "LEAVE AUTHORISATION")

    # Reference number and issue date (top-right)
    txt(f"No.  LV-{leave.pk:04d}", RM - 36*mm, HDR_TOP - 3*mm,   "Helvetica", 7.5, _LABEL)
    txt(_d(leave.created_at),      RM - 36*mm, HDR_TOP - 7.5*mm, "Helvetica", 7.5, _LABEL)

    # Cyan accent line under header
    cv.setStrokeColorRGB(*_CYAN)
    cv.setLineWidth(2.0)
    cv.line(LM, HDR_TOP - HDR_H, RM, HDR_TOP - HDR_H)

    y = HDR_TOP - HDR_H - 3*mm

    # ══════════════════════════════════════════════════════════════════════════
    # EMPLOYEE INFORMATION
    # ══════════════════════════════════════════════════════════════════════════
    y = section_bar(y, "  EMPLOYEE INFORMATION  ·  INFORMATIONS DE L'EMPLOYÉ")
    y = info_row(y, [
        ("Name / Nom",
         f"{emp.user.last_name.upper()} {emp.user.first_name}"),
        ("Employee ID / Matricule",
         emp.employee_id),
    ])
    y = info_row(y, [
        ("Position / Poste",
         emp.position or "—"),
        ("Department / Département",
         str(emp.department) if emp.department else "—"),
    ], alt=True)
    y = info_row(y, [
        ("Date Hired / Date d'embauche",
         _d(emp.date_joined_company)),
        ("Leave Year / Année de Congé",
         str(year)),
    ])
    y -= 2*mm

    # ══════════════════════════════════════════════════════════════════════════
    # LEAVE DETAILS
    # ══════════════════════════════════════════════════════════════════════════
    y = section_bar(y, "  LEAVE DETAILS  ·  DÉTAILS DU CONGÉ")
    y = info_row(y, [
        ("Leave Type / Type de Congé",
         leave.leave_type.name),
        ("Deductible / Déductible",
         "Yes / Oui" if leave.leave_type.is_deductible else "No / Non"),
    ])
    y = info_row(y, [
        ("From / Du",   _d(leave.start_date)),
        ("To / Au",     _d(leave.end_date)),
    ], alt=True)
    y = info_row(y, [
        ("Days Requested / Jours Demandés",
         str(leave.total_days)),
        ("Resume Date / Date de Reprise",
         _d(_resume(leave.end_date))),
    ])
    y = info_row(y, [
        ("Days Available / Jours Disponibles",
         avail_days),
        ("Back-up / Remplaçant",
         leave.backup_employee.user.get_full_name()
         if leave.backup_employee else "—"),
    ], alt=True)
    y -= 2*mm

    # ══════════════════════════════════════════════════════════════════════════
    # REASON FOR LEAVE
    # ══════════════════════════════════════════════════════════════════════════
    REASON_H = 16*mm
    y = section_bar(y, "  REASON FOR LEAVE  ·  MOTIF DE LA DEMANDE")
    frect(LM, y, CW, REASON_H, _CELL_BG, _BORDER, 0.5)
    wraps = simpleSplit(leave.reason or "", "Helvetica", 9, CW - 8*mm)
    ry = y - 4*mm
    for line_str in wraps[:2]:
        txt(line_str, LM + 4*mm, ry, "Helvetica", 9, _DARK)
        ry -= 5*mm
    y -= REASON_H + 2*mm

    # ══════════════════════════════════════════════════════════════════════════
    # REQUESTOR DECLARATION  (employee signs here)
    # ══════════════════════════════════════════════════════════════════════════
    DECL_H = 26*mm
    y = section_bar(y, "  REQUESTOR DECLARATION  ·  DÉCLARATION DU DEMANDEUR")
    frect(LM, y, CW, DECL_H, _CELL_BG, _BORDER, 0.5)

    # Left — name
    txt("Name / Nom",             LM + 3*mm, y - 4*mm,  "Helvetica", 7, _LABEL)
    txt(emp.user.get_full_name(), LM + 3*mm, y - 10*mm, "Helvetica-Bold", 9.5, _DARK)

    # Centre — signature image
    sig_x = LM + CW * 0.33
    sig_w = CW * 0.42
    sig_h = 18*mm
    txt("Signature du demandeur", sig_x, y - 4*mm, "Helvetica", 7, _LABEL)
    if not draw_sig(emp, sig_x, y - 5*mm, max_w=sig_w, max_h=sig_h):
        txt(emp.user.get_full_name(), sig_x, y - 16*mm,
            "Helvetica-Oblique", 8.5, _LABEL)

    # Right — date
    date_x = LM + CW * 0.80
    txt("Date",                date_x, y - 4*mm,  "Helvetica", 7, _LABEL)
    txt(_d(leave.created_at), date_x, y - 10*mm, "Helvetica-Bold", 9.5, _DARK)

    y -= DECL_H + 2*mm

    # ══════════════════════════════════════════════════════════════════════════
    # APPROVALS  — 2 × 2 grid
    # ══════════════════════════════════════════════════════════════════════════
    y = section_bar(y, "  APPROVALS  ·  VISAS D'AUTORISATION")

    # ── Unit Head fallback ────────────────────────────────────────────────────
    # If there is no dedicated Unit Head action on this leave, the Line Manager
    # acted in that capacity — display the Line Manager's info in that cell.
    if leave.unit_head_action_by:
        uh_emp  = leave.unit_head_action_by
        uh_date = _d(leave.unit_head_action_date)
    elif leave.manager_action_by:
        uh_emp  = leave.manager_action_by
        uh_date = _d(leave.manager_action_date)
    else:
        uh_emp  = None
        uh_date = "—"

    approvers = [
        ("UNIT HEAD / CHEF D'UNITÉ",                uh_emp,                   uh_date),
        ("LINE MANAGER / SUPERVISEUR",               leave.manager_action_by,  _d(leave.manager_action_date)),
        ("HR MANAGER / RESP. RESSOURCES HUMAINES",   leave.hr_action_by,       _d(leave.hr_action_date)),
        ("ADMIN DIRECTOR / DIRECTEUR ADMINISTRATIF", leave.director_action_by, _d(leave.director_action_date)),
    ]

    CELL_W = CW / 2
    CELL_H = 35*mm
    CHDR_H = 7*mm

    for idx, (col_label, emp_obj, act_date) in enumerate(approvers):
        row = idx // 2
        col = idx % 2
        cx      = LM + col * CELL_W
        row_top = y - row * CELL_H

        # Cell header bar — logo cyan background, dark text
        frect(cx, row_top, CELL_W, CHDR_H, _CYAN, _BORDER, 0.5)
        cv.setFillColorRGB(*_DARK)
        cv.setFont("Helvetica-Bold", 7)
        cv.drawCentredString(cx + CELL_W / 2, row_top - CHDR_H + 2*mm, col_label)

        # Cell body — cyan-tinted background
        body_top = row_top - CHDR_H
        body_h   = CELL_H - CHDR_H          # ≈ 28 mm
        bg = _ALT_BG if (idx % 2 == 0) else _CELL_BG
        frect(cx, body_top, CELL_W, body_h, bg, _BORDER, 0.5)

        if emp_obj:
            txt(emp_obj.user.get_full_name(),
                cx + 3*mm, body_top - 5*mm,
                "Helvetica-Bold", 9, _DARK)
            txt(act_date,
                cx + 3*mm, body_top - 10.5*mm,
                "Helvetica", 7.5, _LABEL)
            drawn = draw_sig(
                emp_obj,
                cx + 3*mm,
                body_top - 12*mm,
                max_w=CELL_W - 6*mm,
                max_h=body_h - 14*mm,
            )
            if not drawn:
                txt("(signed)",
                    cx + 3*mm, body_top - body_h / 2,
                    "Helvetica-Oblique", 8, _LABEL)
        else:
            txt("Awaiting approval...",
                cx + 3*mm, body_top - body_h / 2,
                "Helvetica-Oblique", 8.5, _BORDER)

    y -= 2 * CELL_H

    # ══════════════════════════════════════════════════════════════════════════
    # FOOTER
    # ══════════════════════════════════════════════════════════════════════════
    cv.setStrokeColorRGB(*_CYAN)
    cv.setLineWidth(1.5)
    cv.line(LM, 14*mm, RM, 14*mm)

    txt("LeaveDesk HR System  ·  Magrabi Cameroon Eye Institute",
        LM, 9*mm, "Helvetica", 7, _LABEL)
    cv.setFillColorRGB(*_LABEL)
    cv.setFont("Helvetica", 7)
    cv.drawRightString(RM, 9*mm,
                       f"Generated: {_date.today().strftime('%d/%m/%Y')}")

    cv.save()
    buf.seek(0)
    return buf
