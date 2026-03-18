"""
Generate the official Magrabi Cameroon Eye Institute
Leave Authorisation PDF for fully approved leave requests.
"""
from io import BytesIO
from datetime import timedelta

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit


def _fmt_date(d):
    if d is None:
        return ""
    if hasattr(d, "date"):
        d = d.date()
    return d.strftime("%d/%m/%Y")


def _resume_date(end_date):
    """First working day (not Sunday) after end_date."""
    d = end_date + timedelta(days=1)
    while d.weekday() == 6:  # skip Sunday
        d += timedelta(days=1)
    return d


def generate_leave_pdf(leave):
    """Return a BytesIO containing the PDF for this LeaveRequest."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4   # 595.28 x 841.89 pt

    emp  = leave.employee
    year = leave.start_date.year

    # ── Leave balance ────────────────────────────────────────────────────────
    try:
        bal = emp.leave_balances.get(year=year)
        total_avail  = bal.total_available
        carried      = bal.carried_forward
    except Exception:
        total_avail = ""
        carried     = ""

    # ── Helper shortcuts ─────────────────────────────────────────────────────
    L = 20 * mm       # left margin
    R = W - 20 * mm   # right margin
    MID = W / 2       # page centre

    def bold(size=9):
        c.setFont("Helvetica-Bold", size)

    def normal(size=9):
        c.setFont("Helvetica", size)

    def label_line(label, value, y, label_x=None, value_x=None, line_end=None):
        """Draw bold label + value + underline."""
        lx = label_x if label_x is not None else L
        vx = value_x if value_x is not None else lx + (len(label) * 5.2 * mm / 10)
        le = line_end if line_end is not None else R
        bold(9.5)
        c.drawString(lx, y, label)
        normal(9.5)
        if value:
            c.drawString(vx + 1 * mm, y, str(value))
        c.setLineWidth(0.5)
        c.line(vx, y - 1.5, le, y - 1.5)

    # ════════════════════════════════════════════════════════════════════════
    # HEADER
    # ════════════════════════════════════════════════════════════════════════
    bold(10)
    c.drawRightString(R, H - 15 * mm, "MAGRABI CAMEROON")
    c.drawRightString(R, H - 20 * mm, "EYE INSTITUTE")

    # Horizontal rule under institution name
    c.setLineWidth(1.0)
    c.line(L, H - 23 * mm, R, H - 23 * mm)

    bold(13)
    c.drawCentredString(MID, H - 31 * mm, "DEMANDE / REQUEST")
    bold(11)
    c.drawCentredString(MID, H - 38 * mm, "AUTORISATION D'ABSENCE / AUTHORISATION OF ABSENCE")

    # ════════════════════════════════════════════════════════════════════════
    # NUMBERED FIELDS
    # ════════════════════════════════════════════════════════════════════════
    LH = 9.5 * mm   # line height
    y  = H - 50 * mm

    # 1. Last name
    bold(9.5); c.drawString(L, y, "1.  Nom/Last name:")
    normal(9.5); c.drawString(L + 46 * mm, y, emp.user.last_name.upper())
    c.line(L + 45 * mm, y - 1.5, R, y - 1.5)
    y -= LH

    # 2. First name
    bold(9.5); c.drawString(L, y, "2.  Prénoms/First Name:")
    normal(9.5); c.drawString(L + 55 * mm, y, emp.user.first_name)
    c.line(L + 54 * mm, y - 1.5, R, y - 1.5)
    y -= LH

    # 3. Position
    bold(9.5); c.drawString(L, y, "3.  Poste/Position:")
    normal(9.5); c.drawString(L + 48 * mm, y, emp.position or "")
    c.line(L + 47 * mm, y - 1.5, R, y - 1.5)
    y -= LH

    # 4. Hiring date
    bold(9.5); c.drawString(L, y, "4.  Date d'embauche/Hiring Date:")
    normal(9.5); c.drawString(L + 72 * mm, y, _fmt_date(emp.date_joined_company))
    c.line(L + 71 * mm, y - 1.5, R, y - 1.5)
    y -= LH

    # 5. Leave type
    bold(9.5); c.drawString(L, y, "5.  Type: Congé Annuel/Annual Leave Days:")
    normal(9.5); c.drawString(L + 91 * mm, y, leave.leave_type.name)
    c.line(L + 90 * mm, y - 1.5, R, y - 1.5)
    y -= LH

    # 6. Accrued from/to (year boundaries)
    bold(9.5); c.drawString(L, y, "6.  Accrued De/From:")
    normal(9.5); c.drawString(L + 48 * mm, y, f"01/01/{year}")
    c.line(L + 47 * mm, y - 1.5, L + 78 * mm, y - 1.5)
    bold(9.5); c.drawString(L + 80 * mm, y, "A/to")
    normal(9.5); c.drawString(L + 90 * mm, y, f"31/12/{year}")
    c.line(L + 89 * mm, y - 1.5, R, y - 1.5)
    y -= LH

    # 7. Accumulated days
    bold(9.5); c.drawString(L, y, "7.  Jour Accumuler/Accumulated Days:")
    normal(9.5); c.drawString(L + 82 * mm, y, str(total_avail))
    c.line(L + 81 * mm, y - 1.5, R, y - 1.5)
    y -= LH

    # 8. Days requested
    bold(9.5); c.drawString(L, y, "8.  Nombre de jours sollicités/Number of days requested:")
    normal(9.5); c.drawString(L + 120 * mm, y, str(leave.total_days))
    c.line(L + 119 * mm, y - 1.5, R, y - 1.5)
    y -= LH

    # 9. From / to dates
    bold(9.5); c.drawString(L, y, "9.  De/From")
    normal(9.5); c.drawString(L + 27 * mm, y, _fmt_date(leave.start_date))
    c.line(L + 26 * mm, y - 1.5, L + 75 * mm, y - 1.5)
    bold(9.5); c.drawString(L + 77 * mm, y, "to")
    normal(9.5); c.drawString(L + 83 * mm, y, _fmt_date(leave.end_date))
    c.line(L + 82 * mm, y - 1.5, R, y - 1.5)
    y -= LH

    # 10. Reason (can be multi-line)
    bold(9.5); c.drawString(L, y, "10. Motif de la demande/Reason of the Request:")
    y -= 7 * mm
    reason_text = leave.reason or ""
    lines = simpleSplit(reason_text, "Helvetica", 9.5, R - L - 2 * mm)
    normal(9.5)
    for i in range(2):          # max 2 lines on form
        text = lines[i] if i < len(lines) else ""
        c.drawString(L, y, text)
        c.line(L, y - 1.5, R, y - 1.5)
        y -= 7 * mm
    y -= 2 * mm

    # 11. Deductible
    deductible_val = "Yes / Oui" if leave.leave_type.is_deductible else "No / Non"
    bold(9.5); c.drawString(L, y, "11. Deductible des congés annuels/Deductible to annual leaves:")
    normal(9.5); c.drawString(L + 128 * mm, y, deductible_val)
    c.line(L + 127 * mm, y - 1.5, R, y - 1.5)
    y -= LH

    # 12. Back-up employee
    bold(9.5); c.drawString(L, y, "12. Back-up employee/Remplaçant:")
    c.line(L + 72 * mm, y - 1.5, R, y - 1.5)
    y -= LH + 3 * mm

    # ── Requestor signature line ─────────────────────────────────────────────
    bold(9); c.drawString(L, y, "Signature (Demandeur/Requestor):")
    c.line(L + 68 * mm, y - 1.5, L + 120 * mm, y - 1.5)
    bold(9); c.drawString(L + 122 * mm, y, "Date:")
    normal(9); c.drawString(L + 133 * mm, y, _fmt_date(leave.created_at))
    c.line(L + 132 * mm, y - 1.5, R, y - 1.5)
    y -= 8 * mm

    # ════════════════════════════════════════════════════════════════════════
    # APPROVAL TABLE  (two-column box)
    # ════════════════════════════════════════════════════════════════════════
    table_top    = y - 2 * mm
    table_bottom = 35 * mm

    # Outer box + vertical divider
    c.setLineWidth(1.2)
    c.rect(L, table_bottom, R - L, table_top - table_bottom)
    c.line(MID, table_top, MID, table_bottom)

    # Column header row
    header_y = table_top - 8 * mm
    c.setLineWidth(0.8)
    c.line(L, header_y, R, header_y)
    bold(10)
    c.drawCentredString((L + MID) / 2,  header_y + 2.5 * mm, "Superviseur /Line-Manager")
    c.drawCentredString((MID + R) / 2,  header_y + 2.5 * mm, "Responsible RH/HR Manager")

    # ── LEFT column ──────────────────────────────────────────────────────────
    mgr       = leave.manager_action_by
    mgr_last  = mgr.user.last_name.upper()  if mgr else ""
    mgr_first = mgr.user.first_name         if mgr else ""
    mgr_date  = _fmt_date(leave.manager_action_date)
    approved_by_mgr = leave.status not in (
        "rejected_manager", "pending", "cancelled"
    )

    lx = L + 3 * mm
    cy = header_y - 6 * mm
    lh = 6 * mm
    line_end_L = MID - 5 * mm

    bold(8.5); c.drawString(lx, cy, "Unit Head:")
    cy -= lh
    bold(8.5); c.drawString(lx, cy, "Nom/Last name:")
    normal(8.5); c.drawString(lx + 34 * mm, cy, mgr_last)
    c.setLineWidth(0.5); c.line(lx + 33 * mm, cy - 1.5, line_end_L, cy - 1.5)
    cy -= lh
    bold(8.5); c.drawString(lx, cy, "Prénoms/First name:")
    normal(8.5); c.drawString(lx + 40 * mm, cy, mgr_first)
    c.line(lx + 39 * mm, cy - 1.5, line_end_L, cy - 1.5)
    cy -= lh
    bold(8.5); c.drawString(lx, cy, "Date and Signature")
    normal(8.5); c.drawString(lx + 39 * mm, cy, mgr_date)
    c.line(lx + 38 * mm, cy - 1.5, line_end_L, cy - 1.5)
    cy -= lh + 2 * mm
    bold(8.5); c.drawString(lx, cy, "Avis/Opinion:")
    cy -= 5 * mm
    opinion_fav = "Favorable/Favourable:  ✓" if approved_by_mgr else "Favorable/Favourable:  ___"
    opinion_unf = "Défavorable/unfavourable:  ___" if approved_by_mgr else "Défavorable/unfavourable:  ✓"
    bold(8.5)
    c.drawString(lx + 4 * mm, cy, opinion_fav)
    cy -= 5 * mm
    c.drawString(lx + 4 * mm, cy, opinion_unf)
    cy -= 7 * mm

    # Divider between Unit Head and Line Manager
    c.setLineWidth(0.4)
    c.line(L, cy + 3 * mm, MID, cy + 3 * mm)

    bold(8.5); c.drawString(lx, cy, "Line Manager/Superviseur")
    cy -= lh
    bold(8.5); c.drawString(lx, cy, "Nom/Last name:")
    c.setLineWidth(0.5); c.line(lx + 33 * mm, cy - 1.5, line_end_L, cy - 1.5)
    cy -= lh
    bold(8.5); c.drawString(lx, cy, "Prénoms/First name:")
    c.line(lx + 39 * mm, cy - 1.5, line_end_L, cy - 1.5)
    cy -= lh
    bold(8.5); c.drawString(lx, cy, "Date and Signature")
    c.line(lx + 38 * mm, cy - 1.5, line_end_L, cy - 1.5)

    # ── RIGHT column ─────────────────────────────────────────────────────────
    hr_emp    = leave.hr_action_by
    hr_name   = hr_emp.user.get_full_name() if hr_emp else ""
    hr_date   = _fmt_date(leave.hr_action_date)
    director  = leave.director_action_by
    dir_name  = director.user.get_full_name() if director else ""
    dir_date  = _fmt_date(leave.director_action_date)
    resume    = _resume_date(leave.end_date)

    rx = MID + 3 * mm
    ry = header_y - 6 * mm
    line_end_R = R - 3 * mm

    bold(8.5); c.drawString(rx, ry, "Nombre de jours accordés")
    ry -= 5 * mm
    bold(8.5); c.drawString(rx, ry, "Number of days granted:")
    normal(8.5)
    granted = str(leave.total_days) if leave.status == "approved" else ""
    c.drawString(rx + 44 * mm, ry, granted)
    c.setLineWidth(0.5); c.line(rx + 43 * mm, ry - 1.5, line_end_R, ry - 1.5)
    ry -= lh

    bold(8.5); c.drawString(rx, ry, "Du/From:")
    normal(8.5); c.drawString(rx + 19 * mm, ry, _fmt_date(leave.start_date))
    c.line(rx + 18 * mm, ry - 1.5, line_end_R, ry - 1.5)
    ry -= lh

    bold(8.5); c.drawString(rx, ry, "Au/to:")
    normal(8.5); c.drawString(rx + 14 * mm, ry, _fmt_date(leave.end_date))
    c.line(rx + 13 * mm, ry - 1.5, line_end_R, ry - 1.5)
    ry -= lh

    bold(8.5); c.drawString(rx, ry, "Reprise/Resume:")
    normal(8.5); c.drawString(rx + 33 * mm, ry, _fmt_date(resume))
    c.line(rx + 32 * mm, ry - 1.5, line_end_R, ry - 1.5)
    ry -= lh

    bold(8.5); c.drawString(rx, ry, "Date:")
    normal(8.5); c.drawString(rx + 13 * mm, ry, hr_date)
    c.line(rx + 12 * mm, ry - 1.5, line_end_R, ry - 1.5)
    ry -= lh

    bold(8.5); c.drawString(rx, ry, "Signature:")
    normal(8.5); c.drawString(rx + 22 * mm, ry, hr_name)
    c.line(rx + 21 * mm, ry - 1.5, line_end_R, ry - 1.5)
    ry -= 7 * mm

    # Divider before Administrative Director
    c.setLineWidth(0.4)
    c.line(MID, ry + 3 * mm, R, ry + 3 * mm)

    bold(8.5); c.drawString(rx, ry, "Administrative Director/Directeur Administratif")
    ry -= lh
    bold(8.5); c.drawString(rx, ry, "Date:")
    normal(8.5); c.drawString(rx + 13 * mm, ry, dir_date)
    c.setLineWidth(0.5); c.line(rx + 12 * mm, ry - 1.5, line_end_R, ry - 1.5)
    ry -= lh
    bold(8.5); c.drawString(rx, ry, "Signature:")
    normal(8.5); c.drawString(rx + 22 * mm, ry, dir_name)
    c.line(rx + 21 * mm, ry - 1.5, line_end_R, ry - 1.5)

    # ════════════════════════════════════════════════════════════════════════
    # FOOTER
    # ════════════════════════════════════════════════════════════════════════
    c.setLineWidth(0.5)
    c.line(L, table_bottom - 3 * mm, R, table_bottom - 3 * mm)

    normal(7.5)
    c.drawString(L, 28 * mm,
        "Cette fiche remplie doit être déposée au plus tard 48 heures à l'avance.")
    c.drawString(L, 24 * mm,
        "The filled form must be submitted 48 hours in advance by the requester.")

    normal(6.5)
    c.drawString(L, 18 * mm,
        "Authorisation No /225/A/MINSANTE/SG/DCS/SD/3000  |  T No M0990509/TR652W  |  BGFI Bank")
    c.drawString(L, 14 * mm,
        "Address: Obok (route d'Obala)  ·  P.O Box: 59223 Yaoundé Cameroon  ·  Email: info@magrabicameroon.com")

    c.save()
    buf.seek(0)
    return buf
