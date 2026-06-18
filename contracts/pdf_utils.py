"""
Generate a professional Contract Letter PDF for
Magrabi ICO Cameroon Eye Institute — AEF HRM.

Covers CDI (permanent) and CDD/INTERN/WACS (fixed-term).
"""
from io import BytesIO
from datetime import date as _date
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader

# ── Colour palette ───────────────────────────────────────────────────────────
_CYAN   = (0.192, 0.722, 0.812)   # #31b8cf  — bars, lines
_BLUE   = (0.141, 0.588, 0.729)   # #2496ba  — title
_DARK   = (0.024, 0.098, 0.118)   # #06191e  — body text
_LABEL  = (0.086, 0.325, 0.365)   # #16535d  — labels
_BORDER = (0.700, 0.850, 0.900)   # border lines
_WHITE  = (1.0,   1.0,   1.0  )


def _d(d):
    if d is None:
        return "—"
    if hasattr(d, "date"):
        d = d.date()
    return d.strftime("%d %B %Y")


def _logo_path():
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for name in ('logo.jpg', 'LOGO.png'):
        p = os.path.join(base, 'static', name)
        if os.path.exists(p):
            return p
    return None


def _draw_header(c, W, H):
    """Draw letterhead: logo circle + hospital name + thin cyan rule."""
    logo = _logo_path()
    if logo:
        try:
            from PIL import Image as PILImage
            import io as _io
            img = PILImage.open(logo).convert('RGB')
            buf = _io.BytesIO()
            img.save(buf, format='PNG')
            buf.seek(0)
            ir = ImageReader(buf)
            c.drawImage(ir, 14*mm, H - 26*mm, width=20*mm, height=20*mm,
                        preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    c.setFont("Helvetica-Bold", 14)
    c.setFillColorRGB(*_BLUE)
    c.drawString(38*mm, H - 16*mm, "Magrabi ICO Cameroon Eye Institute")
    c.setFont("Helvetica", 9)
    c.setFillColorRGB(*_LABEL)
    c.drawString(38*mm, H - 21*mm, "Africa Eye Foundation  |  hr.micei.org  |  pm@hr.micei.org")

    # Cyan rule
    c.setStrokeColorRGB(*_CYAN)
    c.setLineWidth(2)
    c.line(14*mm, H - 28*mm, W - 14*mm, H - 28*mm)


def _section_bar(c, y, W, label):
    """Draw a filled section header bar."""
    c.setFillColorRGB(*_CYAN)
    c.rect(14*mm, y - 4*mm, W - 28*mm, 7*mm, fill=1, stroke=0)
    c.setFillColorRGB(*_WHITE)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(17*mm, y - 1.5*mm, label.upper())


def _row(c, y, W, label, value, label_w=55):
    """Draw a labelled value row with subtle border."""
    x0, x1 = 14*mm, W - 14*mm
    row_h = 8*mm
    c.setStrokeColorRGB(*_BORDER)
    c.setLineWidth(0.5)
    c.rect(x0, y - row_h + 2*mm, x1 - x0, row_h, fill=0, stroke=1)

    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColorRGB(*_LABEL)
    c.drawString(x0 + 2*mm, y - 3*mm, label)

    c.setFont("Helvetica", 9)
    c.setFillColorRGB(*_DARK)
    c.drawString(x0 + label_w*mm, y - 3*mm, str(value) if value else "—")
    return y - row_h


def _footer(c, page_num, W):
    c.setFont("Helvetica", 7.5)
    c.setFillColorRGB(0.55, 0.55, 0.55)
    today = _date.today().strftime("%d %B %Y")
    c.drawString(14*mm, 10*mm, f"Generated on {today}  |  AEF HRM System  |  hr.micei.org")
    c.drawRightString(W - 14*mm, 10*mm, f"Page {page_num}")
    c.setStrokeColorRGB(*_BORDER)
    c.setLineWidth(0.5)
    c.line(14*mm, 14*mm, W - 14*mm, 14*mm)


def generate_contract_pdf(contract):
    """
    Return a BytesIO containing the contract letter PDF.
    contract: contracts.models.Contract instance
    """
    buf = BytesIO()
    W, H = A4
    c = canvas.Canvas(buf, pagesize=A4)
    c.setTitle(f"Contract — {contract.employee.get_full_name()}")

    emp = contract.employee
    user = emp.user
    is_fixed = contract.contract_type in ('CDD', 'INTERN', 'WACS')

    # ── Page 1 ───────────────────────────────────────────────────────────────
    _draw_header(c, W, H)

    # Document title
    y = H - 36*mm
    c.setFont("Helvetica-Bold", 15)
    c.setFillColorRGB(*_BLUE)
    title_map = {
        'CDI':    "PERMANENT EMPLOYMENT CONTRACT",
        'CDD':    "FIXED-TERM EMPLOYMENT CONTRACT",
        'INTERN': "INTERNSHIP CONTRACT",
        'WACS':   "RESIDENTS CONTRACT",
    }
    title = title_map.get(contract.contract_type, "EMPLOYMENT CONTRACT")
    c.drawCentredString(W / 2, y, title)

    if contract.contract_number:
        y -= 7*mm
        c.setFont("Helvetica", 9)
        c.setFillColorRGB(*_LABEL)
        c.drawCentredString(W / 2, y, f"Ref: {contract.contract_number}")

    y -= 10*mm

    # ── EMPLOYEE INFORMATION ─────────────────────────────────────────────────
    _section_bar(c, y, W, "Employee Information")
    y -= 10*mm
    y = _row(c, y, W, "Full Name",      emp.get_full_name())
    y = _row(c, y, W, "Employee ID",    emp.employee_id)
    y = _row(c, y, W, "Position / Role", emp.position or emp.get_role_display())
    y = _row(c, y, W, "Department",     str(emp.department) if emp.department else "—")
    if emp.nationality:
        y = _row(c, y, W, "Nationality",  emp.nationality)
    if emp.date_of_birth:
        y = _row(c, y, W, "Date of Birth", _d(emp.date_of_birth))

    y -= 6*mm

    # ── CONTRACT DETAILS ─────────────────────────────────────────────────────
    _section_bar(c, y, W, "Contract Details")
    y -= 10*mm

    type_labels = {
        'CDI':    "CDI — Permanent (Contrat à Durée Indéterminée)",
        'CDD':    "CDD — Fixed Term (Contrat à Durée Déterminée)",
        'INTERN': f"Internship — {contract.get_internship_type_display() if contract.internship_type else 'General'}",
        'WACS':   "WACS Residents Contract",
    }
    y = _row(c, y, W, "Contract Type",   type_labels.get(contract.contract_type, contract.contract_type))
    y = _row(c, y, W, "Start Date",      _d(contract.start_date))

    if is_fixed and contract.end_date:
        y = _row(c, y, W, "End Date",    _d(contract.end_date))
        y = _row(c, y, W, "Duration",    contract.duration_display)
    else:
        y = _row(c, y, W, "Duration",    "Open-ended — No fixed end date")

    if contract.working_department:
        y = _row(c, y, W, "Placed in Department", str(contract.working_department))

    y -= 6*mm

    # ── CONTRACT TERMS ───────────────────────────────────────────────────────
    _section_bar(c, y, W, "Terms & Conditions")
    y -= 10*mm

    if contract.contract_type == 'CDI':
        terms = [
            "1.  This contract is concluded for an indefinite period, commencing on the start date above.",
            "2.  Either party may terminate this contract subject to the applicable notice period as provided",
            "     by the Labour Code of Cameroon.",
            "3.  The Employee shall perform the duties associated with their position diligently and in",
            "     accordance with the Hospital's policies and procedures.",
            "4.  Remuneration, leave entitlements, and other conditions of service are governed by the",
            "     Hospital's HR policies and the applicable staff grading schedule.",
            "5.  This contract is subject to the laws of the Republic of Cameroon.",
        ]
    elif contract.contract_type == 'CDD':
        terms = [
            "1.  This contract is concluded for a fixed term as specified above.",
            "2.  It shall expire automatically on the end date indicated above without requiring notice,",
            "     unless renewed in writing by both parties before expiry.",
            "3.  The Employee shall perform the duties associated with their position diligently and in",
            "     accordance with the Hospital's policies and procedures.",
            "4.  Remuneration, leave entitlements, and other conditions of service are governed by the",
            "     Hospital's HR policies and the applicable staff grading schedule.",
            "5.  This contract is subject to the laws of the Republic of Cameroon.",
        ]
    elif contract.contract_type == 'INTERN':
        terms = [
            "1.  This internship agreement is concluded for the period indicated above.",
            "2.  The Intern shall follow all instructions given by their supervisor and comply with the",
            "     Hospital's rules, regulations, and confidentiality requirements.",
            "3.  The Hospital shall provide the Intern with access to relevant resources and a designated",
            "     supervisor for guidance throughout the internship period.",
            "4.  No employment relationship is created by this agreement.",
            "5.  This agreement is governed by the laws of the Republic of Cameroon.",
        ]
    else:  # WACS
        terms = [
            "1.  This Residents Contract covers the training period specified above.",
            "2.  The Resident shall comply with the Hospital's clinical protocols, ethical standards,",
            "     and all applicable WACS training requirements.",
            "3.  The Hospital shall provide appropriate clinical supervision and training facilities.",
            "4.  This contract is subject to the WACS programme regulations and the laws of Cameroon.",
        ]

    c.setFont("Helvetica", 8.5)
    c.setFillColorRGB(*_DARK)
    for line in terms:
        if y < 50*mm:
            # Overflow to next page if needed
            break
        c.drawString(16*mm, y, line)
        y -= 5.5*mm

    if contract.notes:
        y -= 4*mm
        c.setFont("Helvetica-Bold", 8.5)
        c.setFillColorRGB(*_LABEL)
        c.drawString(16*mm, y, "Notes:")
        y -= 5*mm
        c.setFont("Helvetica", 8.5)
        c.setFillColorRGB(*_DARK)
        for line in contract.notes.splitlines():
            c.drawString(16*mm, y, line[:110])
            y -= 5*mm

    y -= 10*mm

    # ── SIGNATURES ───────────────────────────────────────────────────────────
    if y < 55*mm:
        c.showPage()
        _draw_header(c, W, H)
        y = H - 40*mm

    _section_bar(c, y, W, "Signatures")
    y -= 14*mm

    sig_y = y
    col1_x = 16*mm
    col2_x = W / 2 + 8*mm
    line_w = W / 2 - 28*mm

    # Employer side
    c.setFont("Helvetica-Bold", 9)
    c.setFillColorRGB(*_LABEL)
    c.drawString(col1_x, sig_y, "For the Employer")
    c.setFont("Helvetica", 8.5)
    c.setFillColorRGB(*_DARK)
    c.drawString(col1_x, sig_y - 5*mm, "Magrabi ICO Cameroon Eye Institute")

    sig_y -= 22*mm
    c.setStrokeColorRGB(*_CYAN)
    c.setLineWidth(0.8)
    c.line(col1_x, sig_y, col1_x + line_w, sig_y)
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawString(col1_x, sig_y - 4*mm, "Signature & Stamp")
    c.drawString(col1_x, sig_y - 8*mm, "Name: ___________________________")
    c.drawString(col1_x, sig_y - 13*mm, "Date:  ___________________________")

    # Employee side — same starting Y as employer heading
    sig_y = y
    c.setFont("Helvetica-Bold", 9)
    c.setFillColorRGB(*_LABEL)
    c.drawString(col2_x, sig_y, "Employee / Recipient")
    c.setFont("Helvetica", 8.5)
    c.setFillColorRGB(*_DARK)
    c.drawString(col2_x, sig_y - 5*mm, emp.get_full_name())

    sig_y -= 22*mm
    c.setStrokeColorRGB(*_CYAN)
    c.setLineWidth(0.8)
    c.line(col2_x, sig_y, col2_x + line_w, sig_y)
    c.setFont("Helvetica", 8)
    c.setFillColorRGB(0.5, 0.5, 0.5)
    c.drawString(col2_x, sig_y - 4*mm, "Signature")
    c.drawString(col2_x, sig_y - 8*mm, "Name: ___________________________")
    c.drawString(col2_x, sig_y - 13*mm, "Date:  ___________________________")

    _footer(c, 1, W)
    c.save()
    buf.seek(0)
    return buf
