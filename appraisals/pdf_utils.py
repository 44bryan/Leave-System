"""
Africa Eye Foundation — Personnel Appraisal PDF
3-page layout, follows paper form order exactly.
"""
from io import BytesIO
from datetime import date as _date
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as _canvas
from reportlab.lib.utils import simpleSplit, ImageReader

W, H = A4

# ── colours ────────────────────────────────────────────────────────────────
CYAN  = (0.192, 0.722, 0.812)
NAVY  = (0.039, 0.302, 0.412)
DARK  = (0.08,  0.08,  0.08)
GRAY  = (0.40,  0.40,  0.40)
LGRAY = (0.95,  0.96,  0.97)
WHITE = (1.0,   1.0,   1.0)
BORD  = (0.75,  0.87,  0.92)
RED   = (0.75,  0.10,  0.10)
GREEN = (0.10,  0.55,  0.25)

LM = 14 * mm          # left margin
RM = W - 14 * mm      # right margin
TM = H - 12 * mm      # top margin
BM = 14 * mm          # bottom margin
CW = RM - LM          # content width


# ── helpers ─────────────────────────────────────────────────────────────────

def _fmt_date(d):
    if d is None:
        return "—"
    if hasattr(d, 'date'):
        d = d.date()
    return d.strftime("%d %b %Y")


def _load_sig(b64):
    if not b64 or not b64.startswith('data:image/'):
        return None
    try:
        from PIL import Image as PILImage
        import io as _io, base64 as _b
        raw = _b.b64decode(b64.split(',', 1)[1])
        img = PILImage.open(_io.BytesIO(raw))
        img.load()
        # flatten transparency
        if img.mode in ('RGBA', 'LA', 'P'):
            bg = PILImage.new('RGBA', img.size, (255, 255, 255, 255))
            bg.paste(img.convert('RGBA'), mask=img.convert('RGBA').split()[3])
            img = bg.convert('RGB')
        else:
            img = img.convert('RGB')
        out = _io.BytesIO()
        img.save(out, format='PNG')
        return ImageReader(_io.BytesIO(out.getvalue()))
    except Exception:
        return None


def _logo_path():
    return os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'static', 'LOGO.png'
    )


# ── PDF builder ──────────────────────────────────────────────────────────────

class Builder:
    """
    Cursor-based PDF builder.  `self.y` is always the TOP of the next thing
    to draw.  Every draw call consumes vertical space and lowers self.y.
    Call need(h) before drawing — it inserts a page break if necessary.
    """

    def __init__(self, buf):
        self.cv = _canvas.Canvas(buf, pagesize=A4)
        self.y = TM
        self._page = 1

    # ── page management ─────────────────────────────────────────────────────

    def _header(self, record):
        cv = self.cv
        # cyan top bar
        cv.setFillColorRGB(*CYAN)
        cv.rect(0, H - 10 * mm, W, 10 * mm, fill=1, stroke=0)
        # logo
        lp = _logo_path()
        if os.path.exists(lp):
            cv.drawImage(lp, LM, H - 10 * mm - 17 * mm,
                         width=46 * mm, height=17 * mm,
                         preserveAspectRatio=True, mask='auto')
        # centre title
        cx = LM + 50 * mm + (CW - 50 * mm) / 2
        cv.setFillColorRGB(*NAVY)
        cv.setFont('Helvetica-Bold', 13)
        cv.drawCentredString(cx, H - 10 * mm - 8 * mm, 'PERSONNEL APPRAISAL')
        cv.setFont('Helvetica', 8.5)
        cv.setFillColorRGB(*GRAY)
        cv.drawCentredString(cx, H - 10 * mm - 14 * mm, 'Africa Eye Foundation')
        # right: cycle info + page
        cv.setFont('Helvetica', 7.5)
        cv.drawRightString(RM, H - 10 * mm - 7 * mm,
                           f'Trim {record.cycle.trimester}  ·  {record.cycle.year}')
        cv.drawRightString(RM, H - 10 * mm - 13 * mm, f'Page {self._page}')
        # divider
        cv.setStrokeColorRGB(*CYAN)
        cv.setLineWidth(1.2)
        cv.line(LM, H - 10 * mm - 19 * mm, RM, H - 10 * mm - 19 * mm)

    def _footer(self, record):
        cv = self.cv
        cv.setStrokeColorRGB(*CYAN)
        cv.setLineWidth(0.8)
        cv.line(LM, BM - 2 * mm, RM, BM - 2 * mm)
        cv.setFont('Helvetica', 7)
        cv.setFillColorRGB(*GRAY)
        cv.drawString(LM, BM - 5.5 * mm, 'AEF HRM  ·  Africa Eye Foundation')
        cv.drawRightString(RM, BM - 5.5 * mm,
                           f'Generated: {_date.today().strftime("%d %b %Y")}')

    def new_page(self, record):
        self._footer(record)
        self.cv.showPage()
        self._page += 1
        self._header(record)
        self.y = H - 10 * mm - 22 * mm

    def need(self, h, record):
        """Ensure h pts of space; start a new page if not enough."""
        if self.y - h < BM + 4 * mm:
            self.new_page(record)

    # ── primitives ──────────────────────────────────────────────────────────

    def rect(self, x, y_top, w, h, fill, stroke=None, lw=0.5):
        cv = self.cv
        cv.setFillColorRGB(*fill)
        if stroke:
            cv.setStrokeColorRGB(*stroke)
            cv.setLineWidth(lw)
            cv.rect(x, y_top - h, w, h, fill=1, stroke=1)
        else:
            cv.rect(x, y_top - h, w, h, fill=1, stroke=0)

    def text(self, s, x, y, font='Helvetica', size=8.5, color=DARK):
        cv = self.cv
        cv.setFillColorRGB(*color)
        cv.setFont(font, size)
        cv.drawString(x, y, str(s))

    def text_c(self, s, x, y, font='Helvetica', size=8.5, color=DARK):
        cv = self.cv
        cv.setFillColorRGB(*color)
        cv.setFont(font, size)
        cv.drawCentredString(x, y, str(s))

    def text_r(self, s, x, y, font='Helvetica', size=8.5, color=DARK):
        cv = self.cv
        cv.setFillColorRGB(*color)
        cv.setFont(font, size)
        cv.drawRightString(x, y, str(s))

    def wrapped_lines(self, text, max_w, font='Helvetica', size=8.5):
        return simpleSplit(text or '', font, size, max_w)

    def draw_wrapped(self, text, x, y_top, max_w,
                     font='Helvetica', size=8.5, color=DARK,
                     line_h=4.8 * mm, max_lines=None):
        lines = self.wrapped_lines(text, max_w, font, size)
        if max_lines:
            lines = lines[:max_lines]
        cy = y_top - line_h
        for ln in lines:
            self.text(ln, x, cy, font, size, color)
            cy -= line_h
        return cy  # bottom of last line

    def sig_image(self, b64, x, y_top, max_w=55 * mm, max_h=13 * mm):
        reader = _load_sig(b64)
        if not reader:
            return
        try:
            self.cv.drawImage(reader, x, y_top - max_h,
                              width=max_w, height=max_h,
                              preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    # ── section header bar ──────────────────────────────────────────────────

    def section_bar(self, label, record, h=6 * mm):
        self.need(h + 2 * mm, record)
        self.rect(LM, self.y, CW, h, NAVY)
        self.text(label, LM + 3 * mm, self.y - h + 2 * mm,
                  'Helvetica-Bold', 8, WHITE)
        self.y -= h + 1 * mm

    # ── info row block (2 columns) ───────────────────────────────────────────

    def info_row(self, left_label, left_val, right_label, right_val,
                 bg=WHITE, rh=10 * mm):
        hw = CW / 2
        self.rect(LM,      self.y, hw, rh, bg, BORD, 0.4)
        self.rect(LM + hw, self.y, hw, rh, bg, BORD, 0.4)
        self.text(left_label,  LM + 2 * mm,      self.y - 3 * mm, size=6.5, color=GRAY)
        self.text(str(left_val or '—'), LM + 2 * mm, self.y - 7.5 * mm,
                  'Helvetica-Bold', 9)
        self.text(right_label, LM + hw + 2 * mm, self.y - 3 * mm, size=6.5, color=GRAY)
        self.text(str(right_val or '—'), LM + hw + 2 * mm, self.y - 7.5 * mm,
                  'Helvetica-Bold', 9)
        self.y -= rh

    # ── text block ──────────────────────────────────────────────────────────

    def text_block(self, label, text, record, min_h=12 * mm):
        lines = self.wrapped_lines(text or '—', CW - 8 * mm)
        h = max(min_h, len(lines) * 4.8 * mm + 10 * mm)
        self.need(h + 6 * mm, record)
        # label strip
        self.rect(LM, self.y, CW, 5.5 * mm, LGRAY, BORD, 0.4)
        self.text(label, LM + 2 * mm, self.y - 4 * mm, size=7, color=GRAY)
        self.y -= 5.5 * mm
        # content
        self.rect(LM, self.y, CW, h, WHITE, BORD, 0.4)
        cy = self.y - 4 * mm
        for ln in lines[:8]:
            self.text(ln, LM + 3 * mm, cy, size=8.5)
            cy -= 4.8 * mm
        self.y -= h + 1 * mm

    # ── rating table (1–5 circles) ───────────────────────────────────────────

    def rating_table(self, rows, values, record,
                     x=None, w=None, col_w=8 * mm, row_h=6.5 * mm, hdr_h=5.5 * mm,
                     check_break=True):
        x = x if x is not None else LM
        w = w if w is not None else CW
        lbl_w = w - 5 * col_w
        needed = hdr_h + len(rows) * row_h + 2 * mm
        if check_break:
            self.need(needed, record)

        # column headers 1-5
        self.rect(x, self.y, w, hdr_h, NAVY)
        for i in range(5):
            cx = x + lbl_w + i * col_w + col_w / 2
            self.text_c(str(i + 1), cx, self.y - hdr_h + 1.5 * mm,
                        'Helvetica-Bold', 7.5, WHITE)
        self.y -= hdr_h

        for idx, (field, label) in enumerate(rows):
            bg = LGRAY if idx % 2 else WHITE
            self.rect(x, self.y, w, row_h, bg, BORD, 0.4)
            # truncate long labels
            disp = label if len(label) <= 42 else label[:39] + '…'
            self.text(disp, x + 2 * mm, self.y - row_h + 2.2 * mm, size=7.5)
            val = values.get(field)
            cv = self.cv
            for i in range(5):
                cx = x + lbl_w + i * col_w + col_w / 2
                cy = self.y - row_h / 2 - 0.5 * mm
                r = 2.0 * mm
                cv.setStrokeColorRGB(*BORD)
                cv.setLineWidth(0.5)
                cv.circle(cx, cy, r, fill=0, stroke=1)
                if val is not None and val == i + 1:
                    cv.setFillColorRGB(*CYAN)
                    cv.circle(cx, cy, r - 0.5, fill=1, stroke=0)
            self.y -= row_h
        self.y -= 2 * mm

    # ── signature block ─────────────────────────────────────────────────────

    def sig_block(self, signed_by, signed_at, sig_b64, record, label='Signature'):
        """Draw a single-row signature strip: Name | Date | Signature image."""
        h = 16 * mm
        self.need(h + 2 * mm, record)
        self.rect(LM, self.y, CW, h, LGRAY, BORD, 0.4)
        name = signed_by.get_full_name() if signed_by else '—'
        self.text('Name:', LM + 2 * mm, self.y - 4 * mm, size=7, color=GRAY)
        self.text(name,    LM + 2 * mm, self.y - 8.5 * mm, 'Helvetica-Bold', 8.5)
        self.text('Date:', LM + 2 * mm, self.y - 13 * mm, size=7, color=GRAY)
        self.text(_fmt_date(signed_at), LM + 12 * mm, self.y - 13 * mm, size=8)
        # signature image on right side
        self.text(label + ':', LM + CW * 0.50, self.y - 4 * mm, size=7, color=GRAY)
        self.sig_image(sig_b64 or '', LM + CW * 0.50, self.y - 2 * mm,
                       max_w=CW * 0.46, max_h=12 * mm)
        self.y -= h + 2 * mm

    # ── comment + signature section ─────────────────────────────────────────

    def comment_section(self, title, comment, signed_by, signed_at, sig_b64, record):
        lines = self.wrapped_lines(comment or '—', CW - 8 * mm)
        h = max(14 * mm, len(lines) * 4.8 * mm + 8 * mm)
        self.need(5.5 * mm + h + 18 * mm + 4 * mm, record)
        # header strip
        self.rect(LM, self.y, CW, 5.5 * mm, NAVY)
        self.text(title, LM + 3 * mm, self.y - 4 * mm, 'Helvetica-Bold', 8, WHITE)
        self.y -= 5.5 * mm
        # comment body
        self.rect(LM, self.y, CW, h, WHITE, BORD, 0.4)
        cy = self.y - 4 * mm
        for ln in lines[:10]:
            self.text(ln, LM + 3 * mm, cy, size=8.5)
            cy -= 4.8 * mm
        self.y -= h
        # sig strip
        self.sig_block(signed_by, signed_at, sig_b64, record)


# ── rating rows definitions ──────────────────────────────────────────────────

PF_ROWS = [
    ('pf_quality_of_work',      'Quality of Work'),
    ('pf_quantity_of_work',     'Quantity of Work'),
    ('pf_knowledge_techniques', 'Knowledge of Techniques'),
    ('pf_ability_to_learn',     'Ability / Interest to Learn'),
]
AA_ROWS = [
    ('aa_motivation',          'Motivation and Initiative'),
    ('aa_attitude_colleagues', 'Attitude towards Colleagues and Authority'),
    ('aa_relations_patients',  'Relations with Patients and Visitors'),
    ('aa_judgment_team',       'Judgment, Team Spirit and Discretion'),
    ('aa_punctuality',         'Punctuality, Attendance, Availability and Honesty'),
    ('aa_presentation',        'Personal Presentation and Professional Secrets'),
]
MGR_PF_ROWS = [(f'mgr_{f}', lbl) for f, lbl in PF_ROWS]
MGR_AA_ROWS = [(f'mgr_{f}', lbl) for f, lbl in AA_ROWS]


# ── main entry point ─────────────────────────────────────────────────────────

def generate_appraisal_pdf(record):
    buf = BytesIO()
    b = Builder(buf)
    cv = b.cv
    rec = record
    emp = record.employee
    disc = record.discipline_deductions()

    # ═══════════════════════════════════════════════════════════════════════
    # PAGE 1  — Header + Employee Info + Tasks + Self-Rating + Appraiser Rating
    # ═══════════════════════════════════════════════════════════════════════
    b._header(rec)
    b.y = H - 10 * mm - 22 * mm

    # ── Employee Information ─────────────────────────────────────────────
    b.section_bar('EMPLOYEE INFORMATION', rec)
    b.info_row('Name / Nom', emp.user.get_full_name(),
               'Position / Poste', emp.position, bg=WHITE)
    b.info_row('Department', str(emp.department or '—'),
               'Date Hired', _fmt_date(emp.date_joined_company), bg=LGRAY)
    b.info_row('Period / Trimestre', rec.cycle.get_trimester_dates(),
               'Year / Année', str(rec.cycle.year), bg=WHITE)
    b.y -= 2 * mm

    # ── Job Identification & Tasks ───────────────────────────────────────
    b.section_bar('1 & 2.  JOB IDENTIFICATION & TASKS', rec)
    b.text_block('Summary of main job attributions / tasks:', rec.tasks_summary, rec)
    b.text_block('Tasks assimilated by the employee:', rec.tasks_assimilated, rec)

    # ── Mastery legend ───────────────────────────────────────────────────
    b.need(6 * mm, rec)
    b.text('Mastery: 1 = Does not meet  2 = Some difficulties  3 = Meets requirements'
           '  4 = Exceeds  5 = Greatly exceeds',
           LM, b.y - 1.5 * mm, size=6.5, color=GRAY)
    b.y -= 6 * mm

    # ── Section 3: Appraisee Self-Rating (employee) ──────────────────────
    b.section_bar('3.  APPRAISEE SELF-RATING  (Filled by Employee)', rec)

    half = CW / 2 - 1 * mm
    pf_h = 5 * mm + 5.5 * mm + len(PF_ROWS) * 6.5 * mm + 2 * mm
    aa_h = 5 * mm + 5.5 * mm + len(AA_ROWS) * 6.5 * mm + 2 * mm
    b.need(max(pf_h, aa_h), rec)

    y_top = b.y
    b.text('Performance Factors', LM + 2 * mm, y_top - 1.5 * mm, 'Helvetica-Bold', 7.5, NAVY)
    b.y = y_top - 5 * mm
    self_pf_vals = {f: getattr(rec, f) for f, _ in PF_ROWS}
    b.rating_table(PF_ROWS, self_pf_vals, rec, x=LM, w=half, check_break=False)
    y_left = b.y

    b.y = y_top
    b.text('Attitude & Aptitude Factors', LM + half + 3 * mm, y_top - 1.5 * mm, 'Helvetica-Bold', 7.5, NAVY)
    b.y = y_top - 5 * mm
    self_aa_vals = {f: getattr(rec, f) for f, _ in AA_ROWS}
    b.rating_table(AA_ROWS, self_aa_vals, rec, x=LM + half + 2 * mm, w=half, check_break=False)
    b.y = min(y_left, b.y)

    # ═══════════════════════════════════════════════════════════════════════
    # PAGE 2  — Goals, Discipline, Awards, Employee sig, Co-worker, Supervisor
    # ═══════════════════════════════════════════════════════════════════════
    b.new_page(rec)

    # ── Section 5: Goals ────────────────────────────────────────────────
    b.section_bar('5.  GOALS TO REACH  (Agreed Action Points)', rec)
    b.text_block('Goals:', rec.goals_to_reach, rec, min_h=14 * mm)

    # ── Section 6: Disciplinary Sanctions ───────────────────────────────
    b.section_bar('6.  DISCIPLINARY SANCTIONS RECEIVED  (–1 per sanction)', rec)
    sanctions = [
        ('verbal_warning',  'Verbal Warning'),
        ('written_caution', 'Written Caution / Request for Written Explanation'),
        ('final_warning',   'Written Warning / Final Written Warning'),
        ('suspension',      'Written Reprimand / Suspension'),
        ('dismissal',       'Dismissal'),
    ]
    rh = 6 * mm
    col_yes = CW * 0.72
    col_no  = CW * 0.86
    b.need((len(sanctions) + 2) * rh, rec)
    # header
    b.rect(LM, b.y, CW, rh, LGRAY, BORD, 0.4)
    b.text('Sanction Type', LM + 2 * mm, b.y - 4 * mm, 'Helvetica-Bold', 7.5, GRAY)
    b.text_c('YES', LM + col_yes + CW * 0.07, b.y - 4 * mm, 'Helvetica-Bold', 7.5, GRAY)
    b.text_c('NO',  LM + col_no  + CW * 0.07, b.y - 4 * mm, 'Helvetica-Bold', 7.5, GRAY)
    b.y -= rh
    for idx, (key, label) in enumerate(sanctions):
        bg = WHITE if idx % 2 else LGRAY
        b.rect(LM, b.y, CW, rh, bg, BORD, 0.4)
        b.text(label, LM + 2 * mm, b.y - rh + 2 * mm, size=7.5)
        count = disc['counts'].get(key, 0)
        cy_mid = b.y - rh / 2
        if count:
            b.text_c('✓', LM + col_yes + CW * 0.07, cy_mid - 1 * mm, 'Helvetica-Bold', 10, RED)
        else:
            b.text_c('✓', LM + col_no  + CW * 0.07, cy_mid - 1 * mm, 'Helvetica-Bold', 10, GREEN)
        b.y -= rh
    # total deduction row
    b.rect(LM, b.y, CW, rh, LGRAY, BORD, 0.5)
    b.text('Total Deduction:', LM + 2 * mm, b.y - 4 * mm, 'Helvetica-Bold', 8, GRAY)
    color = RED if disc['deduction'] < 0 else DARK
    b.text(str(disc['deduction']), LM + col_yes - 8 * mm, b.y - 4 * mm,
           'Helvetica-Bold', 10, color)
    b.y -= rh + 2 * mm

    # ── Section 7: Awards ────────────────────────────────────────────────
    b.section_bar('7.  AWARDS RECEIVED  (+1 per award)', rec)
    awards_list = [
        ('Employee of the Month', rec.award_employee_of_month),
        (f'Other: {rec.award_other or "—"}', bool(rec.award_other)),
    ]
    b.need((len(awards_list) + 1) * rh, rec)
    b.rect(LM, b.y, CW, rh, LGRAY, BORD, 0.4)
    b.text('Award', LM + 2 * mm, b.y - 4 * mm, 'Helvetica-Bold', 7.5, GRAY)
    b.text_c('YES', LM + col_yes + CW * 0.07, b.y - 4 * mm, 'Helvetica-Bold', 7.5, GRAY)
    b.text_c('NO',  LM + col_no  + CW * 0.07, b.y - 4 * mm, 'Helvetica-Bold', 7.5, GRAY)
    b.y -= rh
    for idx, (label, has_it) in enumerate(awards_list):
        bg = WHITE if idx % 2 else LGRAY
        b.rect(LM, b.y, CW, rh, bg, BORD, 0.4)
        b.text(label, LM + 2 * mm, b.y - rh + 2 * mm, size=7.5)
        cy_mid = b.y - rh / 2
        if has_it:
            b.text_c('✓', LM + col_yes + CW * 0.07, cy_mid - 1 * mm, 'Helvetica-Bold', 10, GREEN)
        else:
            b.text_c('✓', LM + col_no  + CW * 0.07, cy_mid - 1 * mm, 'Helvetica-Bold', 10, RED)
        b.y -= rh
    b.y -= 2 * mm

    # ── Section 8: Employee Comments & Signature ─────────────────────────
    b.section_bar('8.  EMPLOYEE COMMENTS & SIGNATURE', rec)
    # three comment columns
    b.need(28 * mm, rec)
    col3 = CW / 3
    for i, (lbl, val) in enumerate([
        ('Comment on Self',         rec.comment_on_self),
        ('Comment on Supervision',  rec.comment_on_supervision),
        ('Comment on Organisation', rec.comment_on_org),
    ]):
        x = LM + i * col3
        b.rect(x, b.y, col3, 5 * mm, LGRAY, BORD, 0.4)
        b.text(lbl, x + 2 * mm, b.y - 3.5 * mm, size=6.5, color=GRAY)
    y_labels = b.y - 5 * mm
    ch = 18 * mm
    for i, (_, val) in enumerate([
        ('', rec.comment_on_self),
        ('', rec.comment_on_supervision),
        ('', rec.comment_on_org),
    ]):
        x = LM + i * col3
        b.rect(x, y_labels, col3, ch, WHITE, BORD, 0.4)
        lines = b.wrapped_lines(val or '—', col3 - 6 * mm, size=7.5)
        cy = y_labels - 3.5 * mm
        for ln in lines[:4]:
            b.text(ln, x + 2 * mm, cy, size=7.5)
            cy -= 4 * mm
    b.y = y_labels - ch - 1 * mm

    # Employee signature
    b.sig_block(rec.employee, rec.employee_signed_at, rec.employee_sig_b64, rec)

    # ── Co-Worker Comment & Signature ────────────────────────────────────
    b.comment_section(
        'CO-WORKER / COLLÈGUE',
        rec.coworker_comment,
        rec.coworker_signed_by,
        rec.coworker_signed_at,
        rec.coworker_sig_b64,
        rec,
    )

    # ── Supervisor: Appraiser Rating + Comment + Signature ───────────────
    b.section_bar('4.  APPRAISER RATING  (Supervisor / Line Manager)', rec)

    mgr_pf_h = 5 * mm + 5.5 * mm + len(MGR_PF_ROWS) * 6.5 * mm + 2 * mm
    mgr_aa_h = 5 * mm + 5.5 * mm + len(MGR_AA_ROWS) * 6.5 * mm + 2 * mm
    b.need(max(mgr_pf_h, mgr_aa_h), rec)

    y_top2 = b.y
    b.text('Performance Factors', LM + 2 * mm, y_top2 - 1.5 * mm, 'Helvetica-Bold', 7.5, NAVY)
    b.y = y_top2 - 5 * mm
    mgr_pf_vals = {f: getattr(rec, f) for f, _ in MGR_PF_ROWS}
    b.rating_table(MGR_PF_ROWS, mgr_pf_vals, rec, x=LM, w=half, check_break=False)
    y_left2 = b.y

    b.y = y_top2
    b.text('Attitude & Aptitude Factors', LM + half + 3 * mm, y_top2 - 1.5 * mm, 'Helvetica-Bold', 7.5, NAVY)
    b.y = y_top2 - 5 * mm
    mgr_aa_vals = {f: getattr(rec, f) for f, _ in MGR_AA_ROWS}
    b.rating_table(MGR_AA_ROWS, mgr_aa_vals, rec, x=LM + half + 2 * mm, w=half, check_break=False)
    b.y = min(y_left2, b.y)

    # Total Ratings by Administration
    b.section_bar('TOTAL RATINGS BY ADMINISTRATION', rec)
    _draw_total_table(b, rec, disc)

    # Supervisor comment + signature
    b.comment_section(
        'SUPERVISOR COMMENT',
        rec.unit_head_comment,
        rec.unit_head_signed_by,
        rec.unit_head_signed_at,
        rec.unit_head_sig_b64,
        rec,
    )

    # ═══════════════════════════════════════════════════════════════════════
    # PAGE 3  — HR, Admin Director, CEO comments
    # ═══════════════════════════════════════════════════════════════════════
    b.new_page(rec)

    b.section_bar('UPPER HIERARCHY COMMENTS & SIGNATURES', rec)

    # HR
    _draw_hierarchy_section(
        b, rec,
        'HR MANAGER / RESP. RESSOURCES HUMAINES',
        rec.hr_comment,
        rec.hr_signed_by,
        rec.hr_signed_at,
        rec.hr_sig_b64,
    )

    # Admin Director
    _draw_hierarchy_section(
        b, rec,
        'ADMINISTRATIVE DIRECTOR / DIRECTEUR ADMINISTRATIF',
        rec.director_comment,
        rec.director_signed_by,
        rec.director_signed_at,
        rec.director_sig_b64,
    )

    # CEO
    _draw_hierarchy_section(
        b, rec,
        'CEO / DIRECTEUR GÉNÉRAL',
        rec.ceo_comment,
        rec.ceo_signed_by,
        rec.ceo_signed_at,
        rec.ceo_sig_b64,
    )

    # Override note
    if rec.has_score_override and rec.score_override_by:
        b.need(8 * mm, rec)
        note = (f'* Scores modified by: {rec.score_override_by.get_full_name()}'
                f'  on {_fmt_date(rec.score_override_at)}')
        b.text(note, LM, b.y - 2 * mm, size=7, color=GRAY)
        b.y -= 7 * mm

    b.y -= 2 * mm

    # Closing note
    b.need(8 * mm, rec)
    b.text(
        'Appraisal feedback to be provided to staff by the end of the first month of the next Trimester.',
        LM, b.y - 2 * mm, size=7.5, color=GRAY,
    )
    b.y -= 6 * mm

    b._footer(rec)
    cv.save()
    buf.seek(0)
    return buf


# ── helper: total ratings table ──────────────────────────────────────────────

def _draw_total_table(b, rec, disc):
    has_override = rec.has_score_override
    if has_override:
        pf_str = (f'{rec.final_performance_score}  '
                  f'(supervisor: {rec.mgr_performance_score or "—"})')
        aa_str = (f'{rec.final_attitude_score}  '
                  f'(supervisor: {rec.mgr_attitude_score or "—"})')
    else:
        pf_str = str(rec.final_performance_score) if rec.final_performance_score is not None else '—'
        aa_str = str(rec.final_attitude_score)     if rec.final_attitude_score     is not None else '—'

    rows = [
        ('1', 'Performance Factors',            '12.5', pf_str),
        ('2', 'Attitude and Aptitude Factors',  '7.5',  aa_str),
        ('3', 'Discipline Sanctions (–1 each)', '',     str(disc['deduction'])),
        ('4', 'Awards / Bonus (+1 each)',        '',     f'+{rec.award_bonus}'),
    ]
    rh = 7 * mm
    col_sn   = 8 * mm
    col_mark = 22 * mm
    col_sc   = 38 * mm
    col_cat  = CW - col_sn - col_mark - col_sc

    total_h = rh * (len(rows) + 1) + 2 * mm
    b.need(total_h, rec)

    # header
    b.rect(LM, b.y, CW, rh, NAVY, BORD, 0.5)
    b.text_c('SN',          LM + col_sn / 2,                      b.y - rh + 2.5 * mm, 'Helvetica-Bold', 8, WHITE)
    b.text('Category',      LM + col_sn + 2 * mm,                 b.y - rh + 2.5 * mm, 'Helvetica-Bold', 8, WHITE)
    b.text_c('Total Marks', LM + col_sn + col_cat + col_mark / 2, b.y - rh + 2.5 * mm, 'Helvetica-Bold', 8, WHITE)
    b.text_c('Score',       LM + col_sn + col_cat + col_mark + col_sc / 2, b.y - rh + 2.5 * mm, 'Helvetica-Bold', 8, WHITE)
    b.y -= rh

    for idx, (sn, cat, marks, score) in enumerate(rows):
        bg = LGRAY if idx % 2 else WHITE
        b.rect(LM, b.y, CW, rh, bg, BORD, 0.5)
        b.text_c(sn,    LM + col_sn / 2,                      b.y - rh + 2.5 * mm, size=8.5)
        b.text(cat,     LM + col_sn + 2 * mm,                 b.y - rh + 2.5 * mm, size=8.5)
        b.text_c(marks, LM + col_sn + col_cat + col_mark / 2, b.y - rh + 2.5 * mm, size=8.5)
        b.text_c(score, LM + col_sn + col_cat + col_mark + col_sc / 2,
                 b.y - rh + 2.5 * mm, 'Helvetica-Bold', 8.5)
        b.y -= rh

    # total row
    b.rect(LM, b.y, CW, rh + 1 * mm, CYAN, BORD, 0.6)
    b.text('TOTAL', LM + col_sn + 2 * mm, b.y - rh + 2.5 * mm, 'Helvetica-Bold', 10, DARK)
    b.text_c('20',  LM + col_sn + col_cat + col_mark / 2, b.y - rh + 2.5 * mm, 'Helvetica-Bold', 10)
    total_str = str(rec.total_score) if rec.total_score is not None else '—'
    b.text_c(total_str, LM + col_sn + col_cat + col_mark + col_sc / 2,
             b.y - rh + 2.5 * mm, 'Helvetica-Bold', 13, NAVY)
    b.y -= rh + 3 * mm


# ── helper: hierarchy comment section ────────────────────────────────────────

def _draw_hierarchy_section(b, rec, title, comment, signed_by, signed_at, sig_b64):
    """Draw a comment + signature block; always rendered even if empty (shows blank lines)."""
    b.comment_section(title, comment, signed_by, signed_at, sig_b64, rec)
