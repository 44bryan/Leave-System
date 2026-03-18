"""
Generate a PDF that replicates the official Magrabi Cameroon Eye Institute
"Autorisation d'Absence" paper form, with all fields pre-filled from the system.
"""
from io import BytesIO
from datetime import timedelta

import os
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit
from reportlab.lib import colors


# ── helpers ──────────────────────────────────────────────────────────────────

def _d(d):
    """Format a date or datetime as DD/MM/YYYY, or return empty string."""
    if d is None:
        return ""
    if hasattr(d, "date"):
        d = d.date()
    return d.strftime("%d/%m/%Y")


def _resume(end_date):
    """First working day (skip Sunday) after end_date."""
    d = end_date + timedelta(days=1)
    while d.weekday() == 6:
        d += timedelta(days=1)
    return d


# ── main generator ────────────────────────────────────────────────────────────

def generate_leave_pdf(leave):
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4          # 595.28 × 841.89 pt

    emp  = leave.employee
    year = leave.start_date.year

    # leave balance
    try:
        bal         = emp.leave_balances.get(year=year)
        total_avail = str(bal.total_available)
    except Exception:
        total_avail = ""

    # margins
    LM = 18 * mm    # left margin
    RM = W - 18 * mm  # right margin
    CW = RM - LM      # content width  ≈ 159 mm

    # ── convenience drawers ───────────────────────────────────────────────────

    def B(size=10):   c.setFont("Helvetica-Bold",   size)
    def N(size=10):   c.setFont("Helvetica",        size)

    def line(x1, y, x2, width=0.6):
        c.setLineWidth(width)
        c.line(x1, y, x2, y)

    def vline(x, y1, y2, width=0.6):
        c.setLineWidth(width)
        c.line(x, y1, x, y2)

    def rect(x, y, w, h, width=0.8):
        c.setLineWidth(width)
        c.rect(x, y, w, h)

    def field(label, value, y, label_w, full_w=None):
        """Draw bold label + underline, write value on underline."""
        fw = full_w or CW
        B(9.5)
        c.drawString(LM, y, label)
        vx = LM + label_w          # where underline starts
        ex = LM + fw               # where underline ends
        line(vx, y - 1.5, ex)
        N(9.5)
        if value:
            # write value slightly inside the underline
            c.drawString(vx + 2 * mm, y, str(value))

    # ═════════════════════════════════════════════════════════════════════════
    # HEADER
    # ═════════════════════════════════════════════════════════════════════════

    # Logo — top left, sized to sit cleanly above the rule line
    logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "LOGO.png")
    RULE_Y = H - 28 * mm   # rule sits here — pushed down to give logo room
    if os.path.exists(logo_path):
        LOGO_H = 22 * mm
        LOGO_W = 60 * mm
        # Bottom of logo = 3 mm above the rule line
        logo_y = RULE_Y + 3 * mm
        c.drawImage(logo_path, LM, logo_y, width=LOGO_W, height=LOGO_H,
                    preserveAspectRatio=True, mask='auto')

    # Thick horizontal rule
    line(LM, RULE_Y, RM, width=1.5)

    # Title block — centred, below the rule
    B(13)
    c.drawCentredString(W / 2, RULE_Y - 8 * mm, "DEMANDE / REQUEST")
    B(11)
    c.drawCentredString(W / 2, RULE_Y - 15 * mm,
                        "AUTORISATION D'ABSENCE / AUTHORISATION OF ABSENCE")

    # ═════════════════════════════════════════════════════════════════════════
    # NUMBERED FIELDS  (1 – 12)
    # ═════════════════════════════════════════════════════════════════════════
    LH = 9 * mm    # line height
    y  = RULE_Y - 26 * mm

    # 1. Last name
    field("1.   Nom/Last name:", emp.user.last_name.upper(), y, 44*mm)
    y -= LH

    # 2. First name
    field("2.   Prenoms /First Name :", emp.user.first_name, y, 55*mm)
    y -= LH

    # 3. Position
    field("3.   Poste/Position :", emp.position or "", y, 44*mm)
    y -= LH

    # 4. Hiring date
    field("4.   Date d'embauche/Hiring Date", _d(emp.date_joined_company), y, 67*mm)
    y -= LH

    # 5. Leave type
    field("5.   Type: Conge Annuel/ Annual Leave Days:", leave.leave_type.name, y, 89*mm)
    y -= LH

    # 6. Accrued From … to …   (split field)
    B(9.5); c.drawString(LM, y, "6.   Accrued De/From:")
    x1 = LM + 47 * mm
    x2 = LM + 80 * mm
    x3 = LM + 88 * mm
    line(x1, y - 1.5, x2)
    N(9.5); c.drawString(x1 + 1*mm, y, f"01/01/{year}")
    B(9.5); c.drawString(x2 + 2*mm, y, "A/to")
    line(x3, y - 1.5, RM)
    N(9.5); c.drawString(x3 + 1*mm, y, f"31/12/{year}")
    y -= LH

    # 7. Accumulated days
    field("7.   Jour Accumuler /Accumulated Days:", total_avail, y, 80*mm)
    y -= LH

    # 8. Days requested
    field("8.   Nombre de jours sollicites/Number of days requested:",
          str(leave.total_days), y, 118*mm)
    y -= LH

    # 9. From … to …   (split field)
    B(9.5); c.drawString(LM, y, "9.   De/From")
    xa = LM + 27 * mm
    xb = LM + 75 * mm
    xc = LM + 82 * mm
    line(xa, y - 1.5, xb)
    N(9.5); c.drawString(xa + 1*mm, y, _d(leave.start_date))
    B(9.5); c.drawString(xb + 2*mm, y, "to")
    line(xc, y - 1.5, RM)
    N(9.5); c.drawString(xc + 1*mm, y, _d(leave.end_date))
    y -= LH

    # 10. Reason  (label on its own line, two underlines below)
    B(9.5); c.drawString(LM, y, "10.  Motif de la demande/Reason of the Request:")
    y -= 6.5 * mm
    reason = leave.reason or ""
    wraps  = simpleSplit(reason, "Helvetica", 9.5, CW - 4*mm)
    for i in range(2):
        txt = wraps[i] if i < len(wraps) else ""
        line(LM, y - 1.5, RM)
        N(9.5); c.drawString(LM + 1*mm, y, txt)
        y -= 6.5 * mm
    y -= 1 * mm

    # 11. Deductible
    ded = "Yes / Oui" if leave.leave_type.is_deductible else "No / Non"
    field("11.  Deductible des conges annuels/Deductible to annual leaves :", ded, y, 125*mm)
    y -= LH

    # 12. Back-up employee
    backup_name = leave.backup_employee.user.get_full_name() if leave.backup_employee else ""
    field("12.  Back-up employee/Remplacant :", backup_name, y, 70*mm)
    y -= LH + 2 * mm

    # ── Requestor signature line ──────────────────────────────────────────────
    B(9)
    c.drawString(LM, y, "Signature (Demandeur/Requestor) :")
    line(LM + 66*mm, y - 1.5, LM + 115*mm)
    N(9); c.drawString(LM + 67*mm, y, emp.user.get_full_name())
    B(9); c.drawString(LM + 117*mm, y, "Date:")
    line(LM + 129*mm, y - 1.5, RM)
    N(9); c.drawString(LM + 130*mm, y, _d(leave.created_at))
    y -= 7 * mm

    # ═════════════════════════════════════════════════════════════════════════
    # APPROVAL TABLE
    # ═════════════════════════════════════════════════════════════════════════
    TABLE_TOP = y - 1 * mm
    MID_X     = LM + CW / 2       # vertical divider

    # Column header row — drawn before content (TABLE_TOP is known)
    HDR_H = 9 * mm
    HDR_Y = TABLE_TOP - HDR_H
    line(LM, HDR_Y, RM, width=1.0)

    B(10)
    c.drawCentredString((LM + MID_X) / 2, HDR_Y + 3*mm, "Superviseur /Line-Manager")
    c.drawCentredString((MID_X + RM)  / 2, HDR_Y + 3*mm, "Responsible RH/HR Manager")

    # ── helper for inside-table fields ───────────────────────────────────────
    def tfield(label, value, y, lx, label_w, ex):
        B(8)
        c.drawString(lx, y, label)
        line(lx + label_w, y - 1.5, ex)
        N(8)
        if value:
            c.drawString(lx + label_w + 1*mm, y, str(value))

    # ── LEFT COLUMN  ─────────────────────────────────────────────────────────
    mgr       = leave.manager_action_by
    mgr_last  = mgr.user.last_name.upper() if mgr else ""
    mgr_first = mgr.user.first_name        if mgr else ""
    mgr_date  = _d(leave.manager_action_date)

    # Unit Head: use unit_head_action_by if set; otherwise fall back to manager info
    uh        = leave.unit_head_action_by
    if uh:
        uh_last  = uh.user.last_name.upper()
        uh_first = uh.user.first_name
        uh_date  = _d(leave.unit_head_action_date)
    else:
        uh_last  = mgr_last
        uh_first = mgr_first
        uh_date  = mgr_date

    LX  = LM + 2*mm
    LE  = MID_X - 3*mm
    cy  = HDR_Y - 5*mm
    lh  = 6 * mm

    B(8); c.drawString(LX, cy, "Unit Head:")
    cy -= lh

    uh_name = (uh_first + " " + uh_last).strip() if (uh_first or uh_last) else ""
    tfield("Nom/Last name:", uh_last,   cy, LX, 30*mm, LE); cy -= lh
    tfield("Prenoms/ First name:", uh_first, cy, LX, 36*mm, LE); cy -= lh
    tfield("Date:",      uh_date,  cy, LX, 12*mm, LE); cy -= lh
    tfield("Signature:", uh_name,  cy, LX, 20*mm, LE); cy -= lh + 1*mm

    B(8); c.drawString(LX, cy, "Avis/Opinion :")
    cy -= 5*mm
    B(8)
    c.drawString(LX + 4*mm, cy, "Favorable/ Favourable:")
    line(LX + 4*mm + 52*mm, cy - 1.5, LE)
    cy -= 5*mm
    c.drawString(LX + 4*mm, cy, "Defavorable/unfavourable:")
    line(LX + 4*mm + 55*mm, cy - 1.5, LE)
    cy -= 6*mm

    # Line Manager section: fill with manager info when no separate unit head
    lm_last  = mgr_last
    lm_first = mgr_first
    lm_date  = mgr_date

    lm_name = (lm_first + " " + lm_last).strip() if (lm_first or lm_last) else ""
    B(8); c.drawString(LX, cy, "Line Manager/Superviseur"); cy -= lh
    tfield("Nom/Last name:",       lm_last,  cy, LX, 30*mm, LE); cy -= lh
    tfield("Prenoms/ First name:", lm_first, cy, LX, 36*mm, LE); cy -= lh
    tfield("Date:",      lm_date,  cy, LX, 12*mm, LE); cy -= lh
    tfield("Signature:", lm_name,  cy, LX, 20*mm, LE)

    # ── RIGHT COLUMN ─────────────────────────────────────────────────────────
    hr_emp   = leave.hr_action_by
    hr_name  = hr_emp.user.get_full_name() if hr_emp else ""
    hr_date  = _d(leave.hr_action_date)
    director = leave.director_action_by
    dir_name = director.user.get_full_name() if director else ""
    dir_date = _d(leave.director_action_date)
    granted  = str(leave.total_days) if leave.status == "approved" else ""
    resume   = _d(_resume(leave.end_date))

    RX  = MID_X + 2*mm
    RE  = RM - 3*mm
    ry  = HDR_Y - 5*mm

    B(8); c.drawString(RX, ry, "Nombre de jours accordes"); ry -= 4*mm
    tfield("Number of days granted:", granted, ry, RX, 42*mm, RE); ry -= lh
    tfield("Du/From:",    _d(leave.start_date),  ry, RX, 18*mm, RE); ry -= lh
    tfield("Au/to:",      _d(leave.end_date),    ry, RX, 14*mm, RE); ry -= lh
    tfield("Reprise /Resume:", resume,            ry, RX, 30*mm, RE); ry -= lh
    tfield("Date:",       hr_date,               ry, RX, 12*mm, RE); ry -= lh
    tfield("Signature:",  hr_name,               ry, RX, 20*mm, RE); ry -= 6*mm

    B(8); c.drawString(RX, ry, "Administrative Director/Directeur Administratif")
    ry -= lh
    tfield("Date:",      dir_date, ry, RX, 12*mm, RE); ry -= lh
    tfield("Signature:", dir_name, ry, RX, 20*mm, RE)

    # Outer border + vertical divider drawn last so TABLE_BOTTOM fits all content
    TABLE_BOTTOM = min(cy, ry) - 5 * mm
    TABLE_H      = TABLE_TOP - TABLE_BOTTOM
    rect(LM, TABLE_BOTTOM, CW, TABLE_H, width=1.5)
    vline(MID_X, TABLE_TOP, TABLE_BOTTOM, width=1.0)

    c.save()
    buf.seek(0)
    return buf
