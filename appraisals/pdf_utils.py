"""
Generate a professional Personnel Appraisal PDF for
Magrabi ICO Cameroon Eye Institute — MICEI HRM.

Layout:
  Page 1 — Header, Employee Info, Job Identification, Appraisee Rating tables
  Page 2 — Goals, Discipline, Awards, Employee Comments + Signature,
            Co-Worker, Unit Head, Manager Rating + Comment
  Page 3 — HR, Director, CEO comments, Total Score table, Footer
"""
from io import BytesIO
from datetime import date as _date
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit, ImageReader

W, H = A4   # 595.28 × 841.89 pt

# ── colour palette ─────────────────────────────────────────────────────────
_CYAN   = (0.192, 0.722, 0.812)   # #31b8cf
_BLUE2  = (0.141, 0.588, 0.729)   # #2496ba
_DARK   = (0.024, 0.098, 0.118)   # #06191e
_LABEL  = (0.086, 0.325, 0.365)   # #16535d
_BORDER = (0.700, 0.850, 0.900)   # #b3d9e6
_WHITE  = (1.0,   1.0,   1.0  )
_LGRAY  = (0.95,  0.97,  0.98 )   # table alt row


LM = 12 * mm
RM = W - 12 * mm
CW = RM - LM


# ── helpers ────────────────────────────────────────────────────────────────

def _d(d):
    if d is None:
        return "—"
    if hasattr(d, 'date'):
        d = d.date()
    return d.strftime("%d/%m/%Y")


def _pil_to_reader(pil_img):
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
    return ImageReader(_io.BytesIO(out.getvalue()))


def _load_sig_b64(b64_str):
    if not b64_str or not b64_str.startswith('data:image/'):
        return None
    try:
        from PIL import Image as PILImage
        import io as _io, base64 as _b64
        raw = _b64.b64decode(b64_str.split(',', 1)[1])
        pil_img = PILImage.open(_io.BytesIO(raw))
        pil_img.load()
        return _pil_to_reader(pil_img)
    except Exception:
        return None


class PDF:
    """Thin wrapper around canvas for convenience."""

    def __init__(self, buf):
        self.cv = canvas.Canvas(buf, pagesize=A4)
        self.logo_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 'static', 'LOGO.png'
        )

    # ── primitives ──────────────────────────────────────────────────────────

    def frect(self, x, y_top, w, h, fill, stroke=None, sw=0.5):
        cv = self.cv
        cv.setLineWidth(sw)
        cv.setFillColorRGB(*fill)
        if stroke:
            cv.setStrokeColorRGB(*stroke)
            cv.rect(x, y_top - h, w, h, fill=1, stroke=1)
        else:
            cv.rect(x, y_top - h, w, h, fill=1, stroke=0)

    def txt(self, s, x, y, font='Helvetica', size=8.5, rgb=_DARK):
        cv = self.cv
        cv.setFillColorRGB(*rgb)
        cv.setFont(font, size)
        cv.drawString(x, y, str(s))

    def txt_r(self, s, x, y, font='Helvetica', size=8.5, rgb=_DARK):
        cv = self.cv
        cv.setFillColorRGB(*rgb)
        cv.setFont(font, size)
        cv.drawRightString(x, y, str(s))

    def txt_c(self, s, x, y, font='Helvetica', size=8.5, rgb=_DARK):
        cv = self.cv
        cv.setFillColorRGB(*rgb)
        cv.setFont(font, size)
        cv.drawCentredString(x, y, str(s))

    def hline(self, y, color=_CYAN, lw=1.5):
        cv = self.cv
        cv.setStrokeColorRGB(*color)
        cv.setLineWidth(lw)
        cv.line(LM, y, RM, y)

    def section_bar(self, y_top, label):
        h = 6.5 * mm
        self.frect(LM, y_top, CW, h, _CYAN)
        self.txt(label, LM + 3 * mm, y_top - h + 2 * mm, 'Helvetica-Bold', 8, _DARK)
        return y_top - h

    def draw_logo(self, x, y, w=48 * mm, h=18 * mm):
        if os.path.exists(self.logo_path):
            self.cv.drawImage(self.logo_path, x, y, width=w, height=h,
                              preserveAspectRatio=True, mask='auto')

    def draw_sig_img(self, b64_str, x, y_top, max_w, max_h):
        reader = _load_sig_b64(b64_str)
        if not reader:
            return False
        try:
            self.cv.drawImage(reader, x, y_top - max_h, width=max_w, height=max_h,
                              preserveAspectRatio=True, mask='auto')
            return True
        except Exception:
            return False

    def wrap_text(self, text, max_w, font='Helvetica', size=8.5):
        return simpleSplit(text or '', font, size, max_w)

    def draw_wrapped(self, text, x, y_top, max_w, font='Helvetica', size=8.5,
                     rgb=_DARK, line_h=4.5 * mm, max_lines=None):
        lines = self.wrap_text(text, max_w, font, size)
        if max_lines:
            lines = lines[:max_lines]
        cy = y_top - line_h
        for line in lines:
            self.txt(line, x, cy, font, size, rgb)
            cy -= line_h
        return cy

    # ── page header / footer ────────────────────────────────────────────────

    def page_header(self, record, page_num):
        cv = self.cv
        # Top cyan bar
        self.frect(0, H, W, 9 * mm, _CYAN)
        # Logo
        self.draw_logo(LM, H - 9 * mm - 18 * mm + 2 * mm)
        # Title
        cx = LM + 50 * mm + (CW - 50 * mm) / 2
        cv.setFillColorRGB(*_BLUE2)
        cv.setFont('Helvetica-Bold', 12)
        cv.drawCentredString(cx, H - 9 * mm - 11 * mm, "PERSONNEL APPRAISAL")
        cv.setFillColorRGB(*_LABEL)
        cv.setFont('Helvetica', 9)
        cv.drawCentredString(cx, H - 9 * mm - 17 * mm, "Magrabi ICO Cameroon Eye Institute")
        # Ref top right
        self.txt(f"Trim {record.cycle.trimester}  ·  {record.cycle.year}",
                 RM - 38 * mm, H - 9 * mm - 8 * mm, size=7.5, rgb=_LABEL)
        self.txt(f"Page {page_num}",
                 RM - 38 * mm, H - 9 * mm - 13 * mm, size=7.5, rgb=_LABEL)
        # Divider
        self.hline(H - 9 * mm - 22 * mm)

    def page_footer(self, record):
        self.hline(12 * mm)
        self.txt(f"MICEI HRM  ·  Magrabi ICO Cameroon Eye Institute",
                 LM, 8 * mm, size=7, rgb=_LABEL)
        self.txt_r(f"Generated: {_date.today().strftime('%d/%m/%Y')}",
                   RM, 8 * mm, size=7, rgb=_LABEL)

    def new_page(self, record, page_num):
        self.page_footer(record)
        self.cv.showPage()
        self.page_header(record, page_num)
        return H - 9 * mm - 26 * mm   # y just below header

    # ── content blocks ──────────────────────────────────────────────────────

    def employee_info(self, y, record):
        emp = record.employee
        y = self.section_bar(y, "  EMPLOYEE INFORMATION  ·  INFORMATIONS DE L'EMPLOYÉ")
        cw2 = CW / 2
        # Row 1
        self.frect(LM,        y, cw2, 11 * mm, _WHITE, _BORDER)
        self.frect(LM + cw2,  y, cw2, 11 * mm, _WHITE, _BORDER)
        self.txt("Name / Nom",           LM + 2 * mm,       y - 3 * mm,  size=7, rgb=_LABEL)
        self.txt(emp.user.get_full_name(), LM + 2 * mm,     y - 8.5 * mm, 'Helvetica-Bold', 9, _DARK)
        self.txt("Position / Poste",      LM + cw2 + 2 * mm, y - 3 * mm, size=7, rgb=_LABEL)
        self.txt(emp.position or '—',     LM + cw2 + 2 * mm, y - 8.5 * mm, 'Helvetica-Bold', 9, _DARK)
        y -= 11 * mm
        # Row 2
        self.frect(LM,        y, cw2, 11 * mm, _LGRAY, _BORDER)
        self.frect(LM + cw2,  y, cw2, 11 * mm, _LGRAY, _BORDER)
        self.txt("Department",             LM + 2 * mm,        y - 3 * mm, size=7, rgb=_LABEL)
        self.txt(str(emp.department or '—'), LM + 2 * mm,      y - 8.5 * mm, 'Helvetica-Bold', 9, _DARK)
        self.txt("Date Hired",             LM + cw2 + 2 * mm,  y - 3 * mm, size=7, rgb=_LABEL)
        self.txt(_d(emp.date_joined_company), LM + cw2 + 2 * mm, y - 8.5 * mm, 'Helvetica-Bold', 9, _DARK)
        y -= 11 * mm
        # Row 3
        self.frect(LM,        y, cw2, 11 * mm, _WHITE, _BORDER)
        self.frect(LM + cw2,  y, cw2, 11 * mm, _WHITE, _BORDER)
        self.txt("Trimester / Période",    LM + 2 * mm,        y - 3 * mm, size=7, rgb=_LABEL)
        self.txt(record.cycle.get_trimester_dates(), LM + 2 * mm, y - 8.5 * mm, 'Helvetica-Bold', 9, _DARK)
        self.txt("Year / Année",           LM + cw2 + 2 * mm,  y - 3 * mm, size=7, rgb=_LABEL)
        self.txt(str(record.cycle.year),   LM + cw2 + 2 * mm,  y - 8.5 * mm, 'Helvetica-Bold', 9, _DARK)
        y -= 11 * mm + 2 * mm
        return y

    def rating_table(self, y, title, rows, values_dict, max_w=None):
        """Draw a 1–5 mastery rating table. rows = [(field, label), ...]"""
        max_w = max_w or CW
        col_w  = 8 * mm
        lbl_w  = max_w - 5 * col_w
        row_h  = 6.5 * mm
        hdr_h  = 6 * mm

        # Sub-header
        self.frect(LM, y, max_w, hdr_h, _BLUE2)
        self.txt(title, LM + 2 * mm, y - hdr_h + 1.8 * mm, 'Helvetica-Bold', 7.5, _WHITE)
        # Column headers 1–5
        for i in range(5):
            cx = LM + lbl_w + i * col_w + col_w / 2
            self.txt_c(str(i + 1), cx, y - hdr_h + 1.8 * mm, 'Helvetica-Bold', 7.5, _WHITE)
        y -= hdr_h

        for idx, (field, label) in enumerate(rows):
            bg = _LGRAY if idx % 2 else _WHITE
            self.frect(LM, y, max_w, row_h, bg, _BORDER, 0.4)
            self.txt(label, LM + 2 * mm, y - row_h + 2 * mm, size=7.5, rgb=_DARK)
            val = values_dict.get(field)
            for i in range(5):
                cx = LM + lbl_w + i * col_w + col_w / 2
                cy = y - row_h / 2 - 1.5 * mm
                r  = 1.8 * mm
                self.cv.setStrokeColorRGB(*_BORDER)
                self.cv.setLineWidth(0.5)
                self.cv.circle(cx, cy, r, fill=0, stroke=1)
                if val is not None and val == i + 1:
                    self.cv.setFillColorRGB(*_CYAN)
                    self.cv.circle(cx, cy, r - 0.5, fill=1, stroke=0)
            y -= row_h
        return y - 1 * mm

    def comment_block(self, y, title, text, signed_by=None, signed_at=None,
                      sig_b64='', min_h=20 * mm):
        lines = self.wrap_text(text or '', CW - 10 * mm, size=8.5)
        block_h = max(min_h, len(lines) * 4.5 * mm + 16 * mm)
        self.frect(LM, y, CW, block_h, _WHITE, _BORDER, 0.5)
        # Title stripe
        self.frect(LM, y, CW, 5.5 * mm, _LGRAY, _BORDER, 0.4)
        self.txt(title, LM + 2 * mm, y - 4 * mm, 'Helvetica-Bold', 7.5, _LABEL)
        # Comment text
        cy = y - 5.5 * mm - 3 * mm
        for line in lines[:8]:
            self.txt(line, LM + 3 * mm, cy, size=8.5, rgb=_DARK)
            cy -= 4.5 * mm
        # Signature area
        sig_y = y - block_h + 3 * mm
        if signed_by:
            name = signed_by.get_full_name() if hasattr(signed_by, 'get_full_name') else str(signed_by)
            self.txt(f"Name: {name}", LM + 3 * mm, sig_y + 9 * mm, size=7, rgb=_LABEL)
            self.txt(f"Date: {_d(signed_at)}", LM + 3 * mm, sig_y + 5 * mm, size=7, rgb=_LABEL)
        sig_x = LM + CW * 0.45
        if sig_b64:
            self.draw_sig_img(sig_b64, sig_x, sig_y + 14 * mm, CW * 0.45, 12 * mm)
        self.txt("Signature:", sig_x, sig_y + 9 * mm, size=7, rgb=_LABEL)
        return y - block_h - 2 * mm


def generate_appraisal_pdf(record):
    buf = BytesIO()
    p = PDF(buf)
    cv = p.cv

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 1
    # ══════════════════════════════════════════════════════════════════════════
    p.page_header(record, 1)
    y = H - 9 * mm - 26 * mm

    # Employee info
    y = p.employee_info(y, record)

    # Job Identification
    y = p.section_bar(y, "  1 & 2. JOB IDENTIFICATION & TASKS")
    # tasks summary
    p.frect(LM, y, CW, 5.5 * mm, _LGRAY, _BORDER, 0.4)
    p.txt("Summary of main job attributions / tasks:", LM + 2 * mm, y - 4 * mm, size=7, rgb=_LABEL)
    y -= 5.5 * mm
    lines = p.wrap_text(record.tasks_summary or '—', CW - 8 * mm, size=8.5)
    block_h = max(10 * mm, len(lines[:4]) * 4.5 * mm + 4 * mm)
    p.frect(LM, y, CW, block_h, _WHITE, _BORDER, 0.4)
    cy = y - 3.5 * mm
    for line in lines[:4]:
        p.txt(line, LM + 3 * mm, cy, size=8.5, rgb=_DARK)
        cy -= 4.5 * mm
    y -= block_h

    p.frect(LM, y, CW, 5.5 * mm, _LGRAY, _BORDER, 0.4)
    p.txt("Tasks assimilated by the employee:", LM + 2 * mm, y - 4 * mm, size=7, rgb=_LABEL)
    y -= 5.5 * mm
    lines2 = p.wrap_text(record.tasks_assimilated or '—', CW - 8 * mm, size=8.5)
    block_h2 = max(10 * mm, len(lines2[:4]) * 4.5 * mm + 4 * mm)
    p.frect(LM, y, CW, block_h2, _WHITE, _BORDER, 0.4)
    cy = y - 3.5 * mm
    for line in lines2[:4]:
        p.txt(line, LM + 3 * mm, cy, size=8.5, rgb=_DARK)
        cy -= 4.5 * mm
    y -= block_h2 + 3 * mm

    # Mastery level legend
    p.txt("Mastery Levels: 1=Does not meet  2=Some difficulties  3=Meets requirements  "
          "4=Exceeds  5=Greatly exceeds",
          LM, y, size=6.5, rgb=_LABEL)
    y -= 5 * mm

    # Self-rating tables
    pf_rows = [
        ('pf_quality_of_work',      'Quality of Work'),
        ('pf_quantity_of_work',     'Quantity of Work'),
        ('pf_knowledge_techniques', 'Knowledge of Techniques'),
        ('pf_ability_to_learn',     'Ability / Interest to Learn'),
    ]
    aa_rows = [
        ('aa_motivation',          'Motivation and Initiative'),
        ('aa_attitude_colleagues', 'Attitude towards Colleagues and Authority'),
        ('aa_relations_patients',  'Relations with Patients and Visitors'),
        ('aa_judgment_team',       'Judgment, Team Spirit and Discretion'),
        ('aa_punctuality',         'Punctuality, Attendance, Availability and Honesty'),
        ('aa_presentation',        'Personal Presentation and Professional Secrets'),
    ]

    # Appraisee vs Appraiser side by side (half width each)
    half = CW / 2 - 1 * mm
    y_start = y

    y = p.section_bar(y, "  3. APPRAISEE RATING (Employee)  ·  4. APPRAISER RATING (Line Manager)")
    y_rating = y

    # Left half — appraisee
    self_vals = {f: getattr(record, f) for f, _ in pf_rows + aa_rows}
    # Right half — appraiser
    mgr_vals = {
        'pf_quality_of_work':      record.mgr_pf_quality_of_work,
        'pf_quantity_of_work':     record.mgr_pf_quantity_of_work,
        'pf_knowledge_techniques': record.mgr_pf_knowledge_techniques,
        'pf_ability_to_learn':     record.mgr_pf_ability_to_learn,
        'aa_motivation':           record.mgr_aa_motivation,
        'aa_attitude_colleagues':  record.mgr_aa_attitude_colleagues,
        'aa_relations_patients':   record.mgr_aa_relations_patients,
        'aa_judgment_team':        record.mgr_aa_judgment_team,
        'aa_punctuality':          record.mgr_aa_punctuality,
        'aa_presentation':         record.mgr_aa_presentation,
    }

    # We'll draw two half-tables side by side using a trick:
    # Save y, draw left, restore y, draw right
    # Performance factors
    y_pf_start = y_rating

    # Left label col width for half-tables — narrower
    col_w  = 6 * mm
    lbl_w  = half - 5 * col_w
    row_h  = 6 * mm
    hdr_h  = 5.5 * mm

    def draw_half_table(x_start, y_top, title, rows, vals, w):
        lbl = w - 5 * col_w
        p.frect(x_start, y_top, w, hdr_h, _BLUE2)
        p.txt(title, x_start + 2 * mm, y_top - hdr_h + 1.5 * mm, 'Helvetica-Bold', 6.5, _WHITE)
        for i in range(5):
            cx = x_start + lbl + i * col_w + col_w / 2
            p.txt_c(str(i + 1), cx, y_top - hdr_h + 1.5 * mm, 'Helvetica-Bold', 6.5, _WHITE)
        yy = y_top - hdr_h
        for idx, (field, label) in enumerate(rows):
            bg = _LGRAY if idx % 2 else _WHITE
            p.frect(x_start, yy, w, row_h, bg, _BORDER, 0.4)
            # Truncate label if needed
            disp = label if len(label) < 38 else label[:35] + '…'
            p.txt(disp, x_start + 2 * mm, yy - row_h + 2 * mm, size=6.5, rgb=_DARK)
            val = vals.get(field)
            for i in range(5):
                cx = x_start + lbl + i * col_w + col_w / 2
                cy = yy - row_h / 2 - 1 * mm
                r  = 1.5 * mm
                cv.setStrokeColorRGB(*_BORDER)
                cv.setLineWidth(0.4)
                cv.circle(cx, cy, r, fill=0, stroke=1)
                if val is not None and val == i + 1:
                    cv.setFillColorRGB(*_CYAN)
                    cv.circle(cx, cy, r - 0.4, fill=1, stroke=0)
            yy -= row_h
        return yy

    y_after_l_pf = draw_half_table(LM, y_rating, "Appraisee — Performance Factors", pf_rows, self_vals, half)
    y_after_r_pf = draw_half_table(LM + half + 2 * mm, y_rating, "Appraiser — Performance Factors", pf_rows, mgr_vals, half)
    y = min(y_after_l_pf, y_after_r_pf) - 1 * mm

    y_after_l_aa = draw_half_table(LM, y, "Appraisee — Attitude & Aptitude Factors", aa_rows, self_vals, half)
    y_after_r_aa = draw_half_table(LM + half + 2 * mm, y, "Appraiser — Attitude & Aptitude Factors", aa_rows, mgr_vals, half)
    y = min(y_after_l_aa, y_after_r_aa) - 3 * mm

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 2
    # ══════════════════════════════════════════════════════════════════════════
    y = p.new_page(record, 2)

    # Goals
    y = p.section_bar(y, "  5. GOALS TO REACH (AGREED ACTION POINTS)")
    lines_g = p.wrap_text(record.goals_to_reach or '—', CW - 8 * mm, size=8.5)
    gh = max(12 * mm, len(lines_g[:4]) * 4.5 * mm + 6 * mm)
    p.frect(LM, y, CW, gh, _WHITE, _BORDER, 0.5)
    cy = y - 4 * mm
    for line in lines_g[:4]:
        p.txt(line, LM + 3 * mm, cy, size=8.5, rgb=_DARK)
        cy -= 4.5 * mm
    y -= gh + 2 * mm

    # Discipline sanctions
    disc = record.discipline_deductions()
    y = p.section_bar(y, "  6. DISCIPLINARY SANCTIONS RECEIVED  (–1 per sanction)")
    sanction_types = [
        ('verbal_warning',  'Verbal Warning'),
        ('written_caution', 'Written Caution / Request for Written Explanation'),
        ('final_warning',   'Written Warning / Final Written Warning'),
        ('suspension',      'Written Reprimand / Suspension'),
        ('dismissal',       'Dismissal'),
    ]
    award_types = [
        ('employee_of_month', 'Employee of the Month'),
        ('other_award',       'Other Rewards'),
    ]
    disc_h = (len(sanction_types) + 1) * 6 * mm
    col_yes = CW * 0.72
    col_no  = CW * 0.84

    p.frect(LM, y, CW, 5.5 * mm, _LGRAY, _BORDER, 0.4)
    p.txt("Sanction Type", LM + 2 * mm, y - 4 * mm, 'Helvetica-Bold', 7.5, _LABEL)
    p.txt_c("YES", LM + col_yes + (CW * 0.12) / 2, y - 4 * mm, 'Helvetica-Bold', 7.5, _LABEL)
    p.txt_c("NO",  LM + col_no  + (CW * 0.16) / 2, y - 4 * mm, 'Helvetica-Bold', 7.5, _LABEL)
    y -= 5.5 * mm
    for idx, (key, label) in enumerate(sanction_types):
        bg = _LGRAY if idx % 2 else _WHITE
        rh = 6 * mm
        p.frect(LM, y, CW, rh, bg, _BORDER, 0.4)
        p.txt(label, LM + 2 * mm, y - rh + 2 * mm, size=7.5, rgb=_DARK)
        count = disc['counts'].get(key, 0)
        cy_mid = y - rh / 2 - 1 * mm
        # YES tick
        if count:
            p.txt_c('✓', LM + col_yes + (CW * 0.12) / 2, cy_mid - 1 * mm, 'Helvetica-Bold', 9, (0.8, 0.1, 0.1))
        else:
            p.txt_c('✓', LM + col_no + (CW * 0.16) / 2, cy_mid - 1 * mm, 'Helvetica-Bold', 9, (0.1, 0.6, 0.3))
        y -= rh

    # Deduction total
    p.frect(LM, y, CW, 6.5 * mm, _LGRAY, _BORDER, 0.5)
    p.txt("Total Deduction:", LM + 2 * mm, y - 4.5 * mm, 'Helvetica-Bold', 8, _LABEL)
    p.txt(str(disc['deduction']), LM + col_yes - 10 * mm, y - 4.5 * mm, 'Helvetica-Bold', 9,
          (0.8, 0.1, 0.1) if disc['deduction'] < 0 else _DARK)
    y -= 6.5 * mm + 2 * mm

    # Awards
    y = p.section_bar(y, "  7. AWARDS RECEIVED  (+1 per award)")
    p.frect(LM, y, CW, 5.5 * mm, _LGRAY, _BORDER, 0.4)
    p.txt("Award", LM + 2 * mm, y - 4 * mm, 'Helvetica-Bold', 7.5, _LABEL)
    p.txt_c("YES", LM + col_yes + (CW * 0.12) / 2, y - 4 * mm, 'Helvetica-Bold', 7.5, _LABEL)
    p.txt_c("NO",  LM + col_no  + (CW * 0.16) / 2, y - 4 * mm, 'Helvetica-Bold', 7.5, _LABEL)
    y -= 5.5 * mm
    awards = [
        ('Employee of the Month', record.award_employee_of_month),
        ('Other Rewards: ' + (record.award_other or '—'), bool(record.award_other)),
    ]
    for idx, (label, has_award) in enumerate(awards):
        bg = _LGRAY if idx % 2 else _WHITE
        rh = 6 * mm
        p.frect(LM, y, CW, rh, bg, _BORDER, 0.4)
        p.txt(label, LM + 2 * mm, y - rh + 2 * mm, size=7.5, rgb=_DARK)
        cy_mid = y - rh / 2 - 1 * mm
        if has_award:
            p.txt_c('✓', LM + col_yes + (CW * 0.12) / 2, cy_mid - 1 * mm, 'Helvetica-Bold', 9, (0.1, 0.6, 0.3))
        else:
            p.txt_c('✓', LM + col_no + (CW * 0.16) / 2, cy_mid - 1 * mm, 'Helvetica-Bold', 9, (0.8, 0.1, 0.1))
        y -= rh
    y -= 2 * mm

    # Employee comments + signature
    y = p.section_bar(y, "  8. EMPLOYEE'S COMMENTS & SIGNATURE")
    emp_comment_h = 30 * mm
    p.frect(LM, y, CW, emp_comment_h, _WHITE, _BORDER, 0.5)
    p.txt("On Self:", LM + 2 * mm, y - 4 * mm, 'Helvetica-Bold', 7, _LABEL)
    p.draw_wrapped(record.comment_on_self or '—', LM + 22 * mm, y - 3 * mm, CW - 24 * mm, size=8, max_lines=2)
    p.txt("On Work Supervision:", LM + 2 * mm, y - 11 * mm, 'Helvetica-Bold', 7, _LABEL)
    p.draw_wrapped(record.comment_on_supervision or '—', LM + 40 * mm, y - 10 * mm, CW - 42 * mm, size=8, max_lines=2)
    p.txt("On Work Organisation:", LM + 2 * mm, y - 18 * mm, 'Helvetica-Bold', 7, _LABEL)
    p.draw_wrapped(record.comment_on_org or '—', LM + 42 * mm, y - 17 * mm, CW - 44 * mm, size=8, max_lines=2)
    # Name + date + sig
    p.txt(f"Name: {record.employee.get_full_name()}", LM + 2 * mm, y - emp_comment_h + 5 * mm, size=7, rgb=_LABEL)
    p.txt(f"Date: {_d(record.employee_signed_at)}", LM + 2 * mm, y - emp_comment_h + 2 * mm, size=7, rgb=_LABEL)
    p.txt("Signature:", LM + CW * 0.40, y - emp_comment_h + 9 * mm, size=7, rgb=_LABEL)
    p.draw_sig_img(record.employee_sig_b64, LM + CW * 0.40, y - emp_comment_h + 13 * mm, CW * 0.55, 10 * mm)
    y -= emp_comment_h + 2 * mm

    # Co-Worker
    y = p.comment_block(y, "CO-WORKER / COLLÈGUE",
                        record.coworker_comment,
                        record.coworker_signed_by, record.coworker_signed_at,
                        record.coworker_sig_b64, min_h=22 * mm)

    # Unit Head
    y = p.comment_block(y, "SUPERVISOR / UNIT HEAD",
                        record.unit_head_comment,
                        record.unit_head_signed_by, record.unit_head_signed_at,
                        record.unit_head_sig_b64, min_h=22 * mm)

    # Manager comment (rating already on page 1)
    y = p.comment_block(y, "LINE MANAGER / SUPERVISEUR  (Appraiser)",
                        record.manager_comment,
                        record.manager_signed_by, record.manager_signed_at,
                        record.manager_sig_b64, min_h=22 * mm)

    # ══════════════════════════════════════════════════════════════════════════
    # PAGE 3
    # ══════════════════════════════════════════════════════════════════════════
    y = p.new_page(record, 3)

    y = p.section_bar(y, "  UPPER HIERARCHY COMMENTS")

    y = p.comment_block(y, "HR MANAGER / RESP. RESSOURCES HUMAINES",
                        record.hr_comment,
                        record.hr_signed_by, record.hr_signed_at,
                        record.hr_sig_b64, min_h=22 * mm)

    y = p.comment_block(y, "ADMINISTRATIVE DIRECTOR / DIRECTEUR ADMINISTRATIF",
                        record.director_comment,
                        record.director_signed_by, record.director_signed_at,
                        record.director_sig_b64, min_h=22 * mm)

    y = p.comment_block(y, "CEO / DIRECTEUR GÉNÉRAL",
                        record.ceo_comment,
                        record.ceo_signed_by, record.ceo_signed_at,
                        record.ceo_sig_b64, min_h=22 * mm)

    y -= 2 * mm

    # Total Ratings Table
    y = p.section_bar(y, "  TOTAL RATINGS BY ADMINISTRATION")
    rows_score = [
        ("1", "Performance Factors",               "12.5", str(record.mgr_performance_score) if record.mgr_performance_score is not None else "—"),
        ("2", "Attitude and Aptitude Factors",      "07.5", str(record.mgr_attitude_score)     if record.mgr_attitude_score is not None else "—"),
        ("3", "Discipline Sanctions (–1 per sanc.)", "",   str(disc['deduction'])),
        ("4", "Awards / Bonus (+1 per award)",       "",   f"+{record.award_bonus}"),
    ]
    col_widths = [8 * mm, CW - 8 * mm - 24 * mm - 24 * mm, 24 * mm, 24 * mm]
    headers    = ["SN", "Category / Catégorie", "Total Marks", "Score"]
    rh = 7 * mm

    # Header row
    p.frect(LM, y, CW, rh, _BLUE2, _BORDER, 0.5)
    cx = LM
    for i, (hdr, cw) in enumerate(zip(headers, col_widths)):
        if i == 0:
            p.txt_c(hdr, cx + cw / 2, y - rh + 2.5 * mm, 'Helvetica-Bold', 8, _WHITE)
        else:
            p.txt(hdr, cx + 2 * mm, y - rh + 2.5 * mm, 'Helvetica-Bold', 8, _WHITE)
        cx += cw
    y -= rh

    for idx, (sn, cat, marks, score) in enumerate(rows_score):
        bg = _LGRAY if idx % 2 else _WHITE
        p.frect(LM, y, CW, rh, bg, _BORDER, 0.5)
        cx = LM
        p.txt_c(sn, cx + col_widths[0] / 2, y - rh + 2.5 * mm, size=8.5, rgb=_DARK)
        cx += col_widths[0]
        p.txt(cat, cx + 2 * mm, y - rh + 2.5 * mm, size=8.5, rgb=_DARK)
        cx += col_widths[1]
        p.txt_c(marks, cx + col_widths[2] / 2, y - rh + 2.5 * mm, size=8.5, rgb=_DARK)
        cx += col_widths[2]
        p.txt_c(score, cx + col_widths[3] / 2, y - rh + 2.5 * mm, 'Helvetica-Bold', 9, _DARK)
        y -= rh

    # Total row
    p.frect(LM, y, CW, rh + 1 * mm, _CYAN, _BORDER, 0.6)
    cx = LM
    p.txt_c("", cx + col_widths[0] / 2, y - rh + 2.5 * mm, 'Helvetica-Bold', 9, _DARK)
    cx += col_widths[0]
    p.txt("TOTAL", cx + 2 * mm, y - rh + 2.5 * mm, 'Helvetica-Bold', 10, _DARK)
    cx += col_widths[1]
    p.txt_c("20", cx + col_widths[2] / 2, y - rh + 2.5 * mm, 'Helvetica-Bold', 10, _DARK)
    cx += col_widths[2]
    total_str = str(record.total_score) if record.total_score is not None else "—"
    p.txt_c(total_str, cx + col_widths[3] / 2, y - rh + 2.5 * mm, 'Helvetica-Bold', 12, _DARK)
    y -= rh + 3 * mm

    p.txt("Appraisal feedback to be provided to staff by the end of the first month of the next Trimester.",
          LM, y, size=7, rgb=_LABEL)

    p.page_footer(record)
    cv.save()
    buf.seek(0)
    return buf
