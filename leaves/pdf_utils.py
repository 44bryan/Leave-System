"""
Generate a professional Leave Authorisation PDF for
Africa Eye Foundation — AEF HRM.

Design: section header bars in logo cyan (#31b8cf), all data cells
        pure white (print-friendly), signatures blend with paper.
"""
from io import BytesIO
from datetime import timedelta, date as _date
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit, ImageReader


# ── colour palette ─────────────────────────────────────────────────────────────
# Bars/headers: logo cyan #31b8cf.  Everything else: pure white (print-safe).
_LOGO   = (0.192, 0.722, 0.812)   # #31b8cf  logo cyan   — section bars, approval headers, lines
_LOGO2  = (0.141, 0.588, 0.729)   # #2496ba  logo blue   — title text, subtitle
_DARK   = (0.024, 0.098, 0.118)   # #06191e  near-black  — body values
_LABEL  = (0.086, 0.325, 0.365)   # #16535d  dark teal   — field labels
_BORDER = (0.700, 0.850, 0.900)   # #b3d9e6  light cyan  — cell outlines (subtle on white)
_WHITE  = (1.0,   1.0,   1.0  )   # pure white — ALL cell/row backgrounds, page


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


def _pil_to_reader(pil_img):
    """Flatten PIL image to RGB and return a ReportLab ImageReader."""
    from PIL import Image as PILImage
    import io as _io
    if pil_img.mode in ('RGBA', 'LA', 'P'):
        rgba = pil_img.convert('RGBA')
        bg = PILImage.new('RGBA', rgba.size, (255, 255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[3])
        pil_img = bg.convert('RGB')
    else:
        pil_img = pil_img.convert('RGB')
    out = _io.BytesIO()
    pil_img.save(out, format='PNG')
    # Use getvalue() so the reader gets a fresh BytesIO at position 0,
    # independent of where 'out' is left after ImageReader reads headers.
    return ImageReader(_io.BytesIO(out.getvalue()))


def _load_sig_b64(b64_str):
    """
    Return an ImageReader from a base64 PNG string, or None.
    This is the primary path — b64 is stored in DB and survives Railway redeploys.
    """
    if not b64_str or not b64_str.startswith('data:image/'):
        return None
    try:
        from PIL import Image as PILImage
        import io as _io
        import base64 as _b64
        raw = _b64.b64decode(b64_str.split(',', 1)[1])
        pil_img = PILImage.open(_io.BytesIO(raw))
        pil_img.load()
        return _pil_to_reader(pil_img)
    except Exception:
        return None


def _load_sig(employee_obj):
    """
    Return a ReportLab ImageReader for the employee's signature, or None.
    Tries employee.signature_b64 first, then falls back to the FileField.
    """
    if not employee_obj:
        return None

    # ── 1. Try DB-stored base64 first (Railway-safe) ─────────────────────────
    reader = _load_sig_b64(getattr(employee_obj, 'signature_b64', '') or '')
    if reader:
        return reader

    # ── 2. Fall back to FileField (local dev or freshly uploaded) ────────────
    try:
        sig = employee_obj.signature
    except Exception:
        return None
    if not sig:
        return None

    try:
        from PIL import Image as PILImage
        import io as _io
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
        return _pil_to_reader(pil_img)
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
        """
        Logo-cyan section header bar with dark text.
        Using the exact logo colour (#31b8cf) so every bar looks identical
        to the logo — no derived/different shade.
        """
        h = 7 * mm
        frect(LM, y_top, CW, h, _LOGO)          # exact logo cyan
        cv.setFillColorRGB(*_DARK)               # dark text for contrast
        cv.setFont("Helvetica-Bold", 8.5)
        cv.drawString(LM + 4*mm, y_top - h + 2.2*mm, label)
        return y_top - h

    def info_row(y_top, pairs, row_h=12*mm, alt=False):
        """One data row: label (small, dark teal) above value (bold dark). Always white background."""
        n  = len(pairs)
        cw = CW / n
        for i, (lbl, val) in enumerate(pairs):
            x = LM + i * cw
            frect(x, y_top, cw, row_h, _WHITE, _BORDER, 0.5)
            txt(lbl,          x + 3*mm, y_top - 4*mm,   "Helvetica",      7,   _LABEL)
            txt(val or "—",   x + 3*mm, y_top - 9.5*mm, "Helvetica-Bold", 9.5, _DARK)
        return y_top - row_h

    def draw_sig(emp_obj, x, y_top, max_w, max_h, stored_b64=''):
        """
        Draw signature within the bounding box.
        Tries stored_b64 (snapshotted on the leave) first, then employee.signature_b64,
        then the FileField — so signatures are always permanent once captured.
        """
        reader = _load_sig_b64(stored_b64) or _load_sig(emp_obj)
        if reader is None:
            return False
        try:
            cv.drawImage(
                reader, x, y_top - max_h,
                width=max_w, height=max_h,
                preserveAspectRatio=True,
                mask='auto',
            )
            return True
        except Exception:
            return False

    # ══════════════════════════════════════════════════════════════════════════
    # TOP ACCENT BAR  — exact logo cyan
    # ══════════════════════════════════════════════════════════════════════════
    frect(0, H, W, 10*mm, _LOGO)

    # ══════════════════════════════════════════════════════════════════════════
    # HEADER  (logo left · title centre · ref top-right)
    # ══════════════════════════════════════════════════════════════════════════
    HDR_TOP = H - 10*mm
    HDR_H   = 28*mm

    logo_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "static", "LOGO.png"
    )
    if os.path.exists(logo_path):
        cv.drawImage(logo_path, LM, HDR_TOP - HDR_H + 4*mm,
                     width=55*mm, height=22*mm,
                     preserveAspectRatio=True, mask='auto')

    title_cx = LM + 55*mm + (CW - 55*mm) / 2
    cv.setFillColorRGB(*_LOGO2)
    cv.setFont("Helvetica-Bold", 13)
    cv.drawCentredString(title_cx, HDR_TOP - 13*mm, "AUTORISATION D'ABSENCE")
    cv.setFillColorRGB(*_LABEL)
    cv.setFont("Helvetica", 10)
    cv.drawCentredString(title_cx, HDR_TOP - 20*mm, "LEAVE AUTHORISATION")

    # Reference number and issue date (top-right)
    txt(f"No.  LV-{leave.pk:04d}", RM - 36*mm, HDR_TOP - 3*mm,   "Helvetica", 7.5, _LABEL)
    txt(_d(leave.created_at),      RM - 36*mm, HDR_TOP - 7.5*mm, "Helvetica", 7.5, _LABEL)

    # Logo-cyan accent line under header — same colour as bars
    cv.setStrokeColorRGB(*_LOGO)
    cv.setLineWidth(2.5)
    cv.line(LM, HDR_TOP - HDR_H, RM, HDR_TOP - HDR_H)

    y = HDR_TOP - HDR_H - 3*mm

    # ══════════════════════════════════════════════════════════════════════════
    # EMPLOYEE INFORMATION
    # ══════════════════════════════════════════════════════════════════════════
    y = section_bar(y, "  EMPLOYEE INFORMATION  ·  INFORMATIONS DE L'EMPLOYÉ")
    y = info_row(y, [
        ("Name / Nom",
         f"{emp.user.last_name} {emp.user.first_name}"),
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
    frect(LM, y, CW, REASON_H, _WHITE, _BORDER, 0.5)
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
    frect(LM, y, CW, DECL_H, _WHITE, _BORDER, 0.5)

    txt("Name / Nom",             LM + 3*mm, y - 4*mm,  "Helvetica", 7, _LABEL)
    txt(emp.user.get_full_name(), LM + 3*mm, y - 10*mm, "Helvetica-Bold", 9.5, _DARK)

    sig_x = LM + CW * 0.33
    sig_w = CW * 0.42
    sig_h = 18*mm
    txt("Signature du demandeur", sig_x, y - 4*mm, "Helvetica", 7, _LABEL)
    if not draw_sig(emp, sig_x, y - 5*mm, max_w=sig_w, max_h=sig_h,
                    stored_b64=leave.employee_sig_b64):
        txt(emp.user.get_full_name(), sig_x, y - 16*mm,
            "Helvetica-Oblique", 8.5, _LABEL)

    date_x = LM + CW * 0.80
    txt("Date",                date_x, y - 4*mm,  "Helvetica", 7, _LABEL)
    txt(_d(leave.created_at), date_x, y - 10*mm, "Helvetica-Bold", 9.5, _DARK)

    y -= DECL_H + 2*mm

    # ══════════════════════════════════════════════════════════════════════════
    # APPROVALS  — 2 × 2 grid
    # ══════════════════════════════════════════════════════════════════════════
    y = section_bar(y, "  APPROVALS  ·  VISAS D'AUTORISATION")

    # Unit Head fallback: if no dedicated unit head acted, the Line Manager
    # filled that role — show their info/signature in the Unit Head cell.
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
        ("UNIT HEAD / CHEF D'UNITÉ",                uh_emp,                   uh_date,                      leave.unit_head_sig_b64),
        ("LINE MANAGER / SUPERVISEUR",               leave.manager_action_by,  _d(leave.manager_action_date), leave.manager_sig_b64),
        ("HR MANAGER / RESP. RESSOURCES HUMAINES",   leave.hr_action_by,       _d(leave.hr_action_date),      leave.hr_sig_b64),
        ("ADMIN DIRECTOR / DIRECTEUR ADMINISTRATIF", leave.director_action_by, _d(leave.director_action_date), leave.director_sig_b64),
    ]

    CELL_W = CW / 2
    CELL_H = 35*mm
    CHDR_H = 7*mm

    for idx, (col_label, emp_obj, act_date, sig_b64) in enumerate(approvers):
        row = idx // 2
        col = idx % 2
        cx      = LM + col * CELL_W
        row_top = y - row * CELL_H

        # Cell header — same exact logo cyan as section bars
        frect(cx, row_top, CELL_W, CHDR_H, _LOGO, _BORDER, 0.5)
        cv.setFillColorRGB(*_DARK)
        cv.setFont("Helvetica-Bold", 7)
        cv.drawCentredString(cx + CELL_W / 2, row_top - CHDR_H + 2*mm, col_label)

        # Cell body
        body_top = row_top - CHDR_H
        body_h   = CELL_H - CHDR_H
        frect(cx, body_top, CELL_W, body_h, _WHITE, _BORDER, 0.5)

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
                stored_b64=sig_b64,
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
    cv.setStrokeColorRGB(*_LOGO)
    cv.setLineWidth(1.5)
    cv.line(LM, 14*mm, RM, 14*mm)

    txt("AEF HRM  ·  Africa Eye Foundation",
        LM, 9*mm, "Helvetica", 7, _LABEL)
    cv.setFillColorRGB(*_LABEL)
    cv.setFont("Helvetica", 7)
    cv.drawRightString(RM, 9*mm,
                       f"Generated: {_date.today().strftime('%d/%m/%Y')}")

    cv.save()
    buf.seek(0)
    return buf
