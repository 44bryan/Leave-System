"""
Generate a professional Leave Authorisation PDF for
Magrabi Cameroon Eye Institute — LeaveDesk HR System.

Design: modern label/value cells, teal section headers,
        2×2 approval grid with embedded signatures.
"""
from io import BytesIO
from datetime import timedelta, date as _date
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit, ImageReader


# ── colour palette ────────────────────────────────────────────────────────────
_TEAL_D = (0.024, 0.302, 0.408)   # #0A4D68  dark teal — bars / title
_TEAL   = (0.031, 0.514, 0.584)   # #088395  mid teal  — approval headers
_DARK   = (0.039, 0.176, 0.267)   # #0a2d45  near-black — values / names
_GRAY   = (0.420, 0.478, 0.553)   # #6b7a8d  medium grey — labels
_LGRAY  = (0.922, 0.933, 0.945)   # #ebaef1  alternating row background
_BORDER = (0.714, 0.773, 0.831)   # #b6c5d4  cell borders
_WHITE  = (1.0,   1.0,   1.0  )


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
    """Return a ReportLab ImageReader for the employee's signature, or None."""
    if not employee_obj or not employee_obj.signature:
        return None
    try:
        from PIL import Image as PILImage
        import io as _io
        try:
            pil_img = PILImage.open(employee_obj.signature.path)
        except Exception:
            with employee_obj.signature.open('rb') as f:
                raw = _io.BytesIO(f.read())
            raw.seek(0)
            pil_img = PILImage.open(raw)
        pil_img.load()
        if pil_img.mode in ('RGBA', 'LA', 'P'):
            pil_img = pil_img.convert('RGBA')
            bg = PILImage.new('RGBA', pil_img.size, (255, 255, 255, 255))
            bg.paste(pil_img, mask=pil_img.split()[3])
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

    def hline(x1, y, x2, rgb=_BORDER, w=0.5):
        cv.setStrokeColorRGB(*rgb)
        cv.setLineWidth(w)
        cv.line(x1, y, x2, y)

    def txt(s, x, y, font="Helvetica", size=9, rgb=_DARK):
        cv.setFillColorRGB(*rgb)
        cv.setFont(font, size)
        cv.drawString(x, y, str(s))

    def ctxt(s, cx, y, font="Helvetica", size=9, rgb=_DARK):
        cv.setFillColorRGB(*rgb)
        cv.setFont(font, size)
        cv.drawCentredString(cx, y, str(s))

    def section_bar(y_top, label):
        """Dark-teal section header bar. Returns new y (below bar)."""
        h = 7 * mm
        frect(LM, y_top, CW, h, _TEAL_D)
        cv.setFillColorRGB(*_WHITE)
        cv.setFont("Helvetica-Bold", 8.5)
        cv.drawString(LM + 4*mm, y_top - h + 2.2*mm, label)
        return y_top - h

    def info_row(y_top, pairs, row_h=12*mm, alt=False):
        """
        One data row split into N equal cells.
        Each cell:  label (small grey)  above  value (bold dark).
        pairs = [(label_str, value_str), ...]
        """
        n  = len(pairs)
        cw = CW / n
        bg = _LGRAY if alt else _WHITE
        for i, (lbl, val) in enumerate(pairs):
            x = LM + i * cw
            frect(x, y_top, cw, row_h, bg, _BORDER, 0.4)
            txt(lbl,          x + 3*mm, y_top - 4*mm,   "Helvetica",      7,   _GRAY)
            txt(val or "—",   x + 3*mm, y_top - 9.5*mm, "Helvetica-Bold", 9.5, _DARK)
        return y_top - row_h

    def draw_sig(emp_obj, x, y_top, max_w, max_h):
        """Draw signature image. Returns True if drawn."""
        reader = _load_sig(emp_obj)
        if reader:
            cv.drawImage(reader, x, y_top - max_h, width=max_w, height=max_h,
                         preserveAspectRatio=True, mask='auto')
            return True
        return False

    # ══════════════════════════════════════════════════════════════════════════
    # TOP ACCENT BAR
    # ══════════════════════════════════════════════════════════════════════════
    frect(0, H, W, 8*mm, _TEAL_D)

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
    cv.setFillColorRGB(*_TEAL_D)
    cv.setFont("Helvetica-Bold", 13)
    cv.drawCentredString(title_cx, HDR_TOP - 13*mm, "AUTORISATION D'ABSENCE")
    cv.setFillColorRGB(*_TEAL)
    cv.setFont("Helvetica", 10)
    cv.drawCentredString(title_cx, HDR_TOP - 20*mm, "LEAVE AUTHORISATION")

    # Reference number and issue date (top-right)
    txt(f"No.  LV-{leave.pk:04d}", RM - 36*mm, HDR_TOP - 3*mm,   "Helvetica", 7.5, _GRAY)
    txt(_d(leave.created_at),      RM - 36*mm, HDR_TOP - 7.5*mm, "Helvetica", 7.5, _GRAY)

    hline(LM, HDR_TOP - HDR_H, RM, _TEAL_D, 1.5)

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
    frect(LM, y, CW, REASON_H, _WHITE, _BORDER, 0.4)
    wraps = simpleSplit(leave.reason or "", "Helvetica", 9, CW - 8*mm)
    ry = y - 4*mm
    for line_str in wraps[:2]:
        txt(line_str, LM + 4*mm, ry, "Helvetica", 9, _DARK)
        ry -= 5*mm
    y -= REASON_H + 2*mm

    # ══════════════════════════════════════════════════════════════════════════
    # REQUESTOR DECLARATION  (employee signs here)
    # ══════════════════════════════════════════════════════════════════════════
    DECL_H = 22*mm
    y = section_bar(y, "  REQUESTOR DECLARATION  ·  DÉCLARATION DU DEMANDEUR")
    frect(LM, y, CW, DECL_H, _WHITE, _BORDER, 0.4)

    # Left — name
    txt("Name / Nom",              LM + 3*mm, y - 4*mm,
        "Helvetica", 7.5, _GRAY)
    txt(emp.user.get_full_name(),  LM + 3*mm, y - 10*mm,
        "Helvetica-Bold", 9.5, _DARK)

    # Centre — signature image
    sig_x = LM + CW * 0.37
    txt("Signature",               sig_x, y - 4*mm, "Helvetica", 7.5, _GRAY)
    if not draw_sig(emp, sig_x, y - 5*mm, max_w=55*mm, max_h=15*mm):
        txt(emp.user.get_full_name(), sig_x, y - 13*mm,
            "Helvetica-Oblique", 8.5, _GRAY)

    # Right — date
    date_x = LM + CW * 0.76
    txt("Date",                    date_x, y - 4*mm,
        "Helvetica", 7.5, _GRAY)
    txt(_d(leave.created_at),      date_x, y - 10*mm,
        "Helvetica-Bold", 9.5, _DARK)

    y -= DECL_H + 2*mm

    # ══════════════════════════════════════════════════════════════════════════
    # APPROVALS  — 2 × 2 grid
    # ══════════════════════════════════════════════════════════════════════════
    y = section_bar(y, "  APPROVALS  ·  VISAS D'AUTORISATION")

    approvers = [
        ("UNIT HEAD / CHEF D'UNITÉ",
         leave.unit_head_action_by,
         _d(leave.unit_head_action_date)),
        ("LINE MANAGER / SUPERVISEUR",
         leave.manager_action_by,
         _d(leave.manager_action_date)),
        ("HR MANAGER / RESP. RESSOURCES HUMAINES",
         leave.hr_action_by,
         _d(leave.hr_action_date)),
        ("ADMIN DIRECTOR / DIRECTEUR ADMINISTRATIF",
         leave.director_action_by,
         _d(leave.director_action_date)),
    ]

    CELL_W = CW / 2
    CELL_H = 33*mm
    CHDR_H = 7*mm

    for idx, (col_label, emp_obj, act_date) in enumerate(approvers):
        row = idx // 2
        col = idx % 2
        cx      = LM + col * CELL_W
        row_top = y - row * CELL_H

        # Cell header bar (mid teal)
        frect(cx, row_top, CELL_W, CHDR_H, _TEAL, _BORDER, 0.5)
        cv.setFillColorRGB(*_WHITE)
        cv.setFont("Helvetica-Bold", 7.5)
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
                cx + 3*mm, body_top - 10*mm,
                "Helvetica", 7.5, _GRAY)
            if not draw_sig(emp_obj, cx + 3*mm, body_top - 11.5*mm,
                            max_w=CELL_W - 6*mm, max_h=14*mm):
                txt("(signed)", cx + 3*mm, body_top - 22*mm,
                    "Helvetica-Oblique", 8, _GRAY)
        else:
            txt("Awaiting approval...",
                cx + 3*mm, body_top - 13*mm,
                "Helvetica-Oblique", 8.5, (0.75, 0.75, 0.75))

    y -= 2 * CELL_H

    # ══════════════════════════════════════════════════════════════════════════
    # FOOTER
    # ══════════════════════════════════════════════════════════════════════════
    hline(LM, 14*mm, RM, _TEAL_D, 0.8)
    txt("LeaveDesk HR System  ·  Magrabi Cameroon Eye Institute",
        LM, 9*mm, "Helvetica", 7, _GRAY)
    cv.setFillColorRGB(*_GRAY)
    cv.setFont("Helvetica", 7)
    cv.drawRightString(RM, 9*mm,
                       f"Generated: {_date.today().strftime('%d/%m/%Y')}")

    cv.save()
    buf.seek(0)
    return buf
