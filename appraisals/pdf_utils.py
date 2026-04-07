"""
Africa Eye Foundation — Personnel Appraisal PDF
Clean 3-page layout. Logo on white. Teal + navy from logo only.
"""
from io import BytesIO
from datetime import date as _date
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as _canvas
from reportlab.lib.utils import simpleSplit, ImageReader

W, H = A4  # 595 x 842 pt

# ── Colors from logo only ────────────────────────────────────────────────────
TEAL  = (0.161, 0.722, 0.788)  # circle teal  #29B8C9
NAVY  = (0.051, 0.471, 0.549)  # text navy    #0D7888
LTEAL = (0.918, 0.969, 0.976)  # light teal bg
WHITE = (1.0,   1.0,   1.0)
INK   = (0.12,  0.12,  0.12)

LM = 12 * mm        # left margin
RM = W - 12 * mm    # right margin
CW = RM - LM        # 171 mm content width
BM = 10 * mm        # bottom margin

HEADER_H = 22 * mm  # white header height
FOOTER_H = 8  * mm


def _d(v):
    if v is None: return '—'
    if hasattr(v, 'date'): v = v.date()
    return v.strftime('%d/%m/%Y')


def _load_sig(b64):
    if not b64 or not b64.startswith('data:image/'): return None
    try:
        from PIL import Image as PI
        import io as _io, base64 as _b
        raw = _b.b64decode(b64.split(',', 1)[1])
        img = PI.open(_io.BytesIO(raw)); img.load()
        if img.mode in ('RGBA', 'LA', 'P'):
            bg = PI.new('RGBA', img.size, (255, 255, 255, 255))
            bg.paste(img.convert('RGBA'), mask=img.convert('RGBA').split()[3])
            img = bg.convert('RGB')
        else:
            img = img.convert('RGB')
        out = _io.BytesIO(); img.save(out, 'PNG')
        return ImageReader(_io.BytesIO(out.getvalue()))
    except Exception:
        return None


def _logo_path():
    return os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'static', 'LOGO.png'
    )


# ─────────────────────────────────────────────────────────────────────────────
class Builder:
    """
    y always points to the TOP of the next element to draw.
    Every draw call moves y down by the element's height.
    need(h) inserts a page break if h won't fit.
    Rating tables: rating_half() does NOT touch self.y — caller manages y.
    """

    def __init__(self, buf, record):
        self.cv  = _canvas.Canvas(buf, pagesize=A4)
        self.rec = record
        self._pg = 0
        self.y   = 0
        self._new_page()

    # ── primitives ───────────────────────────────────────────────────────────

    def _rect(self, x, y_top, w, h, fill, stroke=None, lw=0.4):
        c = self.cv
        c.setFillColorRGB(*fill)
        if stroke:
            c.setStrokeColorRGB(*stroke); c.setLineWidth(lw)
            c.rect(x, y_top - h, w, h, fill=1, stroke=1)
        else:
            c.rect(x, y_top - h, w, h, fill=1, stroke=0)

    def _text(self, s, x, y, font='Helvetica', sz=8.5, col=INK, align='L'):
        c = self.cv
        c.setFillColorRGB(*col); c.setFont(font, sz)
        s = str(s)
        if   align == 'C': c.drawCentredString(x, y, s)
        elif align == 'R': c.drawRightString(x, y, s)
        else:               c.drawString(x, y, s)

    def _wrap(self, text, max_w, font='Helvetica', sz=8.5):
        return simpleSplit(text or '', font, sz, max_w)

    def _sig_img(self, b64, x, y_top, mw, mh):
        r = _load_sig(b64)
        if not r: return
        try:
            self.cv.drawImage(r, x, y_top - mh, width=mw, height=mh,
                              preserveAspectRatio=True, mask='auto')
        except Exception:
            pass

    # ── page management ──────────────────────────────────────────────────────

    def _new_page(self):
        rec  = self.rec
        self._pg += 1
        c    = self.cv

        # ── White header area ────────────────────────────────────────────────
        # Full white rect
        self._rect(0, H, W, HEADER_H, WHITE)

        # Logo on the left (white background so logo is fully visible)
        lp = _logo_path()
        if os.path.exists(lp):
            c.drawImage(lp, LM, H - HEADER_H + 3 * mm,
                        width=46 * mm, height=16 * mm,
                        preserveAspectRatio=True, mask='auto')

        # Title text to the right of the logo
        c.setFillColorRGB(*NAVY)
        c.setFont('Helvetica-Bold', 13)
        c.drawString(LM + 50 * mm, H - 9 * mm, 'PERSONNEL APPRAISAL')
        c.setFont('Helvetica', 8.5)
        c.setFillColorRGB(*TEAL)
        c.drawString(LM + 50 * mm, H - 14 * mm, 'Africa Eye Foundation')

        # Cycle info top-right
        c.setFont('Helvetica', 7.5)
        c.setFillColorRGB(*NAVY)
        c.drawRightString(RM, H - 8 * mm,
                          f'Trimester {rec.cycle.trimester}  ·  {rec.cycle.year}')
        c.drawRightString(RM, H - 14 * mm, f'Page {self._pg}')

        # Teal line under header
        c.setStrokeColorRGB(*TEAL)
        c.setLineWidth(1.8)
        c.line(0, H - HEADER_H, W, H - HEADER_H)

        # Thin navy line just below teal
        c.setStrokeColorRGB(*NAVY)
        c.setLineWidth(0.5)
        c.line(0, H - HEADER_H - 0.8 * mm, W, H - HEADER_H - 0.8 * mm)

        self.y = H - HEADER_H - 2 * mm

    def _end_page(self):
        rec = self.rec
        c   = self.cv
        # footer
        c.setStrokeColorRGB(*TEAL); c.setLineWidth(1.0)
        c.line(0, FOOTER_H, W, FOOTER_H)
        c.setFont('Helvetica', 6.5); c.setFillColorRGB(*NAVY)
        c.drawString(LM, FOOTER_H - 4 * mm, 'AEF HRM  ·  Africa Eye Foundation')
        c.drawRightString(RM, FOOTER_H - 4 * mm,
                          f'Generated: {_date.today().strftime("%d/%m/%Y")}')
        c.showPage()

    def need(self, h):
        if self.y - h < FOOTER_H + 4 * mm:
            self._end_page()
            self._new_page()

    # ── section bar ──────────────────────────────────────────────────────────

    def bar(self, label):
        h = 6 * mm
        self.need(h + 1 * mm)
        self._rect(LM, self.y, CW, h, NAVY)
        self._text(label, LM + 3 * mm, self.y - h + 2 * mm,
                   'Helvetica-Bold', 8, WHITE)
        self.y -= h + 1 * mm

    # ── two-column info row ───────────────────────────────────────────────────

    def info_row(self, ll, lv, rl, rv, shade=False):
        rh  = 9 * mm
        hw  = CW / 2
        bg  = LTEAL if shade else WHITE
        self._rect(LM,      self.y, hw, rh, bg, NAVY, 0.3)
        self._rect(LM + hw, self.y, hw, rh, bg, NAVY, 0.3)
        self._text(ll, LM + 2 * mm,      self.y - 2.5 * mm, sz=6.5, col=NAVY)
        self._text(str(lv or '—'), LM + 2 * mm, self.y - 7 * mm,
                   'Helvetica-Bold', 9)
        self._text(rl, LM + hw + 2 * mm, self.y - 2.5 * mm, sz=6.5, col=NAVY)
        self._text(str(rv or '—'), LM + hw + 2 * mm, self.y - 7 * mm,
                   'Helvetica-Bold', 9)
        self.y -= rh

    # ── text content box ──────────────────────────────────────────────────────

    def text_box(self, label, text, max_lines=4):
        LH = 4.5 * mm
        ls  = self._wrap(text, CW - 5 * mm)[:max_lines]
        bh  = max(9 * mm, len(ls) * LH + 5 * mm)
        self.need(5 * mm + bh + 1 * mm)
        # label strip
        self._rect(LM, self.y, CW, 5 * mm, LTEAL, NAVY, 0.3)
        self._text(label, LM + 2 * mm, self.y - 3.5 * mm, sz=7, col=NAVY)
        self.y -= 5 * mm
        # body
        self._rect(LM, self.y, CW, bh, WHITE, NAVY, 0.3)
        cy = self.y - 3.5 * mm
        for ln in ls:
            self._text(ln, LM + 2.5 * mm, cy, sz=8.5)
            cy -= LH
        self.y -= bh + 1 * mm

    # ── rating table (half-width, does NOT touch self.y) ─────────────────────

    def _rating_table_at(self, rows, vals, x, w, y_top):
        """Draw rating table starting at y_top. Returns bottom y. Does NOT change self.y."""
        col_w = 7.5 * mm
        lbl_w = w - 5 * col_w
        HDR   = 5.5 * mm
        ROW   = 5.5 * mm
        y     = y_top

        # header row with 1-5 labels
        self._rect(x, y, w, HDR, NAVY)
        for i in range(5):
            cx = x + lbl_w + i * col_w + col_w / 2
            self._text(str(i + 1), cx, y - HDR + 1.5 * mm,
                       'Helvetica-Bold', 7.5, WHITE, 'C')
        y -= HDR

        for idx, (field, label) in enumerate(rows):
            bg = LTEAL if idx % 2 else WHITE
            self._rect(x, y, w, ROW, bg, NAVY, 0.3)
            disp = label if len(label) <= 32 else label[:29] + '…'
            self._text(disp, x + 1.5 * mm, y - ROW + 1.5 * mm, sz=7)
            val = vals.get(field)
            c   = self.cv
            for i in range(5):
                cx  = x + lbl_w + i * col_w + col_w / 2
                cy  = y - ROW / 2 - 0.5 * mm
                rad = 1.9 * mm
                c.setStrokeColorRGB(*NAVY); c.setLineWidth(0.4)
                c.circle(cx, cy, rad, fill=0, stroke=1)
                if val is not None and val == i + 1:
                    c.setFillColorRGB(*TEAL)
                    c.circle(cx, cy, rad - 0.4, fill=1, stroke=0)
            y -= ROW
        return y - 1 * mm

    def two_tables(self, left_rows, left_vals, right_rows, right_vals,
                   left_title, right_title):
        """Two rating tables side by side. One need() call. self.y updated after both."""
        half  = CW / 2 - 1 * mm
        # height needed = title + header + rows
        lh = 4 * mm + 5.5 * mm + len(left_rows)  * 5.5 * mm + 1 * mm
        rh = 4 * mm + 5.5 * mm + len(right_rows) * 5.5 * mm + 1 * mm
        self.need(max(lh, rh))

        y0 = self.y
        # sub-titles
        self._text(left_title,  LM + 1 * mm,            y0 - 1.5 * mm, 'Helvetica-Bold', 7.5, NAVY)
        self._text(right_title, LM + half + 2 * mm + 1 * mm, y0 - 1.5 * mm, 'Helvetica-Bold', 7.5, NAVY)
        y_start = y0 - 4 * mm

        y_l = self._rating_table_at(left_rows,  left_vals,  LM,                 half, y_start)
        y_r = self._rating_table_at(right_rows, right_vals, LM + half + 2 * mm, half, y_start)
        self.y = min(y_l, y_r)

    # ── signature strip ───────────────────────────────────────────────────────

    def sig_strip(self, signed_by, signed_at, sig_b64):
        """14mm strip: name + date left, signature image right. Atomic."""
        SH = 15 * mm
        self.need(SH + 1 * mm)
        y = self.y
        self._rect(LM, y, CW, SH, LTEAL, NAVY, 0.3)

        name = signed_by.get_full_name() if signed_by else 'Pending / Not yet signed'
        self._text('Name:',        LM + 2 * mm, y - 3 * mm,   sz=6.5, col=NAVY)
        self._text(name,           LM + 2 * mm, y - 8 * mm,   'Helvetica-Bold', 9)
        self._text('Date:',        LM + 2 * mm, y - 12.5 * mm, sz=6.5, col=NAVY)
        self._text(_d(signed_at),  LM + 11 * mm,y - 12.5 * mm, sz=8.5)

        sig_x = LM + CW * 0.47
        self._text('Signature:', sig_x, y - 3 * mm, sz=6.5, col=NAVY)
        self._sig_img(sig_b64 or '', sig_x, y - 3 * mm,
                      CW * 0.50, SH - 4 * mm)
        self.y = y - SH - 1 * mm

    # ── comment + signature block (fully atomic) ──────────────────────────────

    def comment_block(self, title, comment, signed_by, signed_at, sig_b64,
                      max_lines=6):
        """
        One need() call for: bar (6mm) + comment box + sig strip (15mm).
        Nothing can be split across pages.
        """
        LH  = 4.5 * mm
        BAR = 6   * mm
        SIG = 15  * mm

        lines = self._wrap(comment, CW - 5 * mm)[:max_lines]
        cbh   = max(10 * mm, len(lines) * LH + 5 * mm)
        total = BAR + cbh + SIG + 2 * mm

        self.need(total)
        y = self.y

        # bar
        self._rect(LM, y, CW, BAR, NAVY)
        self._text(title, LM + 3 * mm, y - BAR + 2 * mm,
                   'Helvetica-Bold', 8, WHITE)
        y -= BAR

        # comment body
        self._rect(LM, y, CW, cbh, WHITE, NAVY, 0.3)
        cy = y - 3.5 * mm
        for ln in lines:
            self._text(ln, LM + 2.5 * mm, cy, sz=8.5)
            cy -= LH
        y -= cbh

        # sig strip
        self._rect(LM, y, CW, SIG, LTEAL, NAVY, 0.3)
        name = signed_by.get_full_name() if signed_by else 'Pending / Not yet signed'
        self._text('Name:',         LM + 2 * mm, y - 3 * mm,    sz=6.5, col=NAVY)
        self._text(name,            LM + 2 * mm, y - 8 * mm,    'Helvetica-Bold', 9)
        self._text('Date:',         LM + 2 * mm, y - 12.5 * mm, sz=6.5, col=NAVY)
        self._text(_d(signed_at),   LM + 11 * mm,y - 12.5 * mm, sz=8.5)
        sig_x = LM + CW * 0.47
        self._text('Signature:', sig_x, y - 3 * mm, sz=6.5, col=NAVY)
        self._sig_img(sig_b64 or '', sig_x, y - 3 * mm,
                      CW * 0.50, SIG - 4 * mm)
        y -= SIG

        self.y = y - 2 * mm

    # ── total ratings table ───────────────────────────────────────────────────

    def total_table(self, disc):
        rec = self.rec
        has_ov = rec.has_score_override
        if has_ov:
            pf_s = f'{rec.final_performance_score}  (supervisor: {rec.mgr_performance_score or "—"})'
            aa_s = f'{rec.final_attitude_score}  (supervisor: {rec.mgr_attitude_score or "—"})'
        else:
            pf_s = str(rec.final_performance_score) if rec.final_performance_score is not None else '—'
            aa_s = str(rec.final_attitude_score)     if rec.final_attitude_score     is not None else '—'

        rows = [
            ('1', 'Performance Factors',            '12.5', pf_s),
            ('2', 'Attitude and Aptitude Factors',  '7.5',  aa_s),
            ('3', 'Discipline Sanctions (–1 each)', '',     str(disc['deduction'])),
            ('4', 'Awards / Bonus (+1 each)',        '',     f'+{rec.award_bonus}'),
        ]
        ROW = 7 * mm
        sn  = 9  * mm
        mk  = 22 * mm
        sc  = 30 * mm
        cat = CW - sn - mk - sc

        self.need(ROW * (len(rows) + 1) + 3 * mm)
        y = self.y

        # header
        self._rect(LM, y, CW, ROW, NAVY)
        self._text('SN',          LM + sn/2,             y - ROW + 2.5 * mm, 'Helvetica-Bold', 8, WHITE, 'C')
        self._text('Category',    LM + sn + 2 * mm,      y - ROW + 2.5 * mm, 'Helvetica-Bold', 8, WHITE)
        self._text('Total Marks', LM + sn + cat + mk/2,  y - ROW + 2.5 * mm, 'Helvetica-Bold', 8, WHITE, 'C')
        self._text('Score',       LM + sn + cat + mk + sc/2, y - ROW + 2.5 * mm, 'Helvetica-Bold', 8, WHITE, 'C')
        y -= ROW

        for idx, (sno, cat_, mk_, sc_) in enumerate(rows):
            bg = LTEAL if idx % 2 else WHITE
            self._rect(LM, y, CW, ROW, bg, NAVY, 0.3)
            self._text(sno,  LM + sn/2,              y - ROW + 2.5 * mm, sz=8.5, col=INK, align='C')
            self._text(cat_, LM + sn + 2 * mm,       y - ROW + 2.5 * mm, sz=8.5)
            self._text(mk_,  LM + sn + cat + mk/2,   y - ROW + 2.5 * mm, sz=8.5, col=INK, align='C')
            self._text(sc_,  LM + sn + cat + mk + sc/2, y - ROW + 2.5 * mm,
                       'Helvetica-Bold', 8.5, col=NAVY, align='C')
            y -= ROW

        # total row
        self._rect(LM, y, CW, ROW + 1 * mm, TEAL)
        self._text('TOTAL',    LM + sn + 2 * mm,       y - ROW + 2.5 * mm, 'Helvetica-Bold', 10, WHITE)
        self._text('20',       LM + sn + cat + mk/2,   y - ROW + 2.5 * mm, 'Helvetica-Bold', 10, WHITE, 'C')
        ts = str(rec.total_score) if rec.total_score is not None else '—'
        self._text(ts, LM + sn + cat + mk + sc/2, y - ROW + 2.5 * mm,
                   'Helvetica-Bold', 13, WHITE, 'C')
        y -= ROW + 3 * mm

        if has_ov and rec.score_override_by:
            self._text(
                f'* Scores modified by: {rec.score_override_by.get_full_name()}  ({_d(rec.score_override_at)})',
                LM, y, sz=7, col=NAVY)
            y -= 5 * mm

        self.y = y


# ── rating field definitions ─────────────────────────────────────────────────

PF_ROWS = [
    ('pf_quality_of_work',      'Quality of Work'),
    ('pf_quantity_of_work',     'Quantity of Work'),
    ('pf_knowledge_techniques', 'Knowledge of Techniques'),
    ('pf_ability_to_learn',     'Ability / Interest to Learn'),
]
AA_ROWS = [
    ('aa_motivation',          'Motivation and Initiative'),
    ('aa_attitude_colleagues', 'Attitude towards Colleagues'),
    ('aa_relations_patients',  'Relations with Patients'),
    ('aa_judgment_team',       'Judgment, Team Spirit & Discretion'),
    ('aa_punctuality',         'Punctuality, Attendance & Honesty'),
    ('aa_presentation',        'Personal Presentation & Professionalism'),
]
MGR_PF = [(f'mgr_{f}', l) for f, l in PF_ROWS]
MGR_AA = [(f'mgr_{f}', l) for f, l in AA_ROWS]


# ── entry point ──────────────────────────────────────────────────────────────

def generate_appraisal_pdf(record):
    buf  = BytesIO()
    b    = Builder(buf, record)
    rec  = record
    emp  = record.employee
    disc = record.discipline_deductions()

    # ═══════════════════════════════════════════════════════════════════════
    # PAGE 1 — Employee info · Tasks · Self-rating · Appraiser rating
    # ═══════════════════════════════════════════════════════════════════════

    # Employee Information
    b.bar('EMPLOYEE INFORMATION')
    b.info_row('Name / Nom',        emp.user.get_full_name(),
               'Position / Poste',  emp.position or '—')
    b.info_row('Department',        str(emp.department or '—'),
               'Date Hired',        _d(emp.date_joined_company), shade=True)
    b.info_row('Period / Trimestre', rec.cycle.get_trimester_dates(),
               'Year / Année',       str(rec.cycle.year))
    b.y -= 2 * mm

    # Tasks
    b.bar('1 & 2.  JOB IDENTIFICATION & TASKS')
    b.text_box('Summary of main job attributions / tasks:', rec.tasks_summary)
    b.text_box('Tasks assimilated by the employee:', rec.tasks_assimilated, max_lines=3)

    # Legend
    b.need(4 * mm)
    b._text(
        'Mastery levels:  1 = Does not meet   2 = Some difficulties   '
        '3 = Meets requirements   4 = Exceeds   5 = Greatly exceeds',
        LM, b.y - 1.5 * mm, sz=7, col=NAVY)
    b.y -= 5 * mm

    # Section 3: Appraisee self-rating
    b.bar('3.  APPRAISEE SELF-RATING  (Filled by Employee)')
    self_pf = {f: getattr(rec, f) for f, _ in PF_ROWS}
    self_aa = {f: getattr(rec, f) for f, _ in AA_ROWS}
    b.two_tables(PF_ROWS, self_pf, AA_ROWS, self_aa,
                 'Performance Factors', 'Attitude & Aptitude Factors')
    b.y -= 1 * mm

    # Section 4: Appraiser rating (supervisor)
    b.bar('4.  APPRAISER RATING  (Supervisor / Line Manager)')
    mgr_pf = {f: getattr(rec, f) for f, _ in MGR_PF}
    mgr_aa = {f: getattr(rec, f) for f, _ in MGR_AA}
    b.two_tables(MGR_PF, mgr_pf, MGR_AA, mgr_aa,
                 'Performance Factors', 'Attitude & Aptitude Factors')

    # ═══════════════════════════════════════════════════════════════════════
    # PAGE 2 — Goals · Discipline · Awards · Employee sig · Co-worker · Supervisor · Total
    # ═══════════════════════════════════════════════════════════════════════
    b.need(999)  # force page 2

    # Goals
    b.bar('5.  GOALS TO REACH  (Agreed Action Points)')
    b.text_box('Goals:', rec.goals_to_reach, max_lines=4)

    # Discipline sanctions
    b.bar('6.  DISCIPLINARY SANCTIONS RECEIVED  (–1 per sanction)')
    sanctions = [
        ('verbal_warning',  'Verbal Warning'),
        ('written_caution', 'Written Caution / Request for Written Explanation'),
        ('final_warning',   'Written Warning / Final Written Warning'),
        ('suspension',      'Written Reprimand / Suspension'),
        ('dismissal',       'Dismissal'),
    ]
    RH      = 6 * mm
    col_yes = CW * 0.73
    col_no  = CW * 0.86
    b.need((len(sanctions) + 2) * RH)
    # header
    b._rect(LM, b.y, CW, RH, NAVY)
    b._text('Sanction Type', LM + 2 * mm, b.y - RH + 2 * mm, 'Helvetica-Bold', 8, WHITE)
    b._text('YES', LM + col_yes + CW * 0.065, b.y - RH + 2 * mm, 'Helvetica-Bold', 8, WHITE, 'C')
    b._text('NO',  LM + col_no  + CW * 0.07,  b.y - RH + 2 * mm, 'Helvetica-Bold', 8, WHITE, 'C')
    b.y -= RH
    for idx, (key, label) in enumerate(sanctions):
        bg = LTEAL if idx % 2 else WHITE
        b._rect(LM, b.y, CW, RH, bg, NAVY, 0.3)
        b._text(label, LM + 2 * mm, b.y - RH + 2 * mm, sz=8)
        cy = b.y - RH / 2 - 0.5 * mm
        if disc['counts'].get(key, 0):
            b._text('✓', LM + col_yes + CW * 0.065, cy, 'Helvetica-Bold', 11, TEAL, 'C')
        else:
            b._text('✓', LM + col_no  + CW * 0.07,  cy, 'Helvetica-Bold', 11, NAVY, 'C')
        b.y -= RH
    # deduction total
    b._rect(LM, b.y, CW, RH, LTEAL, NAVY, 0.4)
    b._text('Total Deduction:', LM + 2 * mm, b.y - RH + 2 * mm, 'Helvetica-Bold', 8, NAVY)
    col = TEAL if disc['deduction'] < 0 else NAVY
    b._text(str(disc['deduction']), LM + col_yes - 8 * mm, b.y - RH + 2 * mm,
            'Helvetica-Bold', 10, col)
    b.y -= RH + 2 * mm

    # Awards
    b.bar('7.  AWARDS RECEIVED  (+1 per award)')
    awards_list = [
        ('Employee of the Month', rec.award_employee_of_month),
        (f'Other: {rec.award_other or "—"}', bool(rec.award_other)),
    ]
    b.need((len(awards_list) + 1) * RH)
    b._rect(LM, b.y, CW, RH, NAVY)
    b._text('Award', LM + 2 * mm, b.y - RH + 2 * mm, 'Helvetica-Bold', 8, WHITE)
    b._text('YES', LM + col_yes + CW * 0.065, b.y - RH + 2 * mm, 'Helvetica-Bold', 8, WHITE, 'C')
    b._text('NO',  LM + col_no  + CW * 0.07,  b.y - RH + 2 * mm, 'Helvetica-Bold', 8, WHITE, 'C')
    b.y -= RH
    for idx, (label, has_it) in enumerate(awards_list):
        bg = LTEAL if idx % 2 else WHITE
        b._rect(LM, b.y, CW, RH, bg, NAVY, 0.3)
        b._text(label, LM + 2 * mm, b.y - RH + 2 * mm, sz=8)
        cy = b.y - RH / 2 - 0.5 * mm
        if has_it:
            b._text('✓', LM + col_yes + CW * 0.065, cy, 'Helvetica-Bold', 11, TEAL, 'C')
        else:
            b._text('✓', LM + col_no  + CW * 0.07,  cy, 'Helvetica-Bold', 11, NAVY, 'C')
        b.y -= RH
    b.y -= 2 * mm

    # Section 8: Employee comments + signature
    b.bar('8.  EMPLOYEE COMMENTS & SIGNATURE')
    b.need(5 * mm + 14 * mm + 15 * mm + 1 * mm)
    col3 = CW / 3
    # 3 mini header strips
    for i, lbl in enumerate(['Comment on Self', 'Comment on Supervision', 'Comment on Organisation']):
        x = LM + i * col3
        b._rect(x, b.y, col3, 5 * mm, NAVY)
        b._text(lbl, x + 1.5 * mm, b.y - 3.5 * mm, sz=7, col=WHITE)
    b.y -= 5 * mm
    # 3 mini content boxes
    ch = 14 * mm
    vals = [rec.comment_on_self, rec.comment_on_supervision, rec.comment_on_org]
    for i, val in enumerate(vals):
        x  = LM + i * col3
        b._rect(x, b.y, col3, ch, WHITE, NAVY, 0.3)
        ls = b._wrap(val, col3 - 4 * mm)[:3]
        cy = b.y - 3.5 * mm
        for ln in ls:
            b._text(ln, x + 2 * mm, cy, sz=8); cy -= 4.5 * mm
    b.y -= ch
    b.sig_strip(rec.employee, rec.employee_signed_at, rec.employee_sig_b64)

    # Co-worker
    b.comment_block(
        'CO-WORKER / COLLÈGUE',
        rec.coworker_comment, rec.coworker_signed_by,
        rec.coworker_signed_at, rec.coworker_sig_b64)

    # Supervisor comment
    b.comment_block(
        'SUPERVISOR COMMENT & SIGNATURE  (Appraiser)',
        rec.unit_head_comment, rec.unit_head_signed_by,
        rec.unit_head_signed_at, rec.unit_head_sig_b64)

    # Total Ratings by Administration
    b.bar('TOTAL RATINGS BY ADMINISTRATION')
    b.total_table(disc)

    # ═══════════════════════════════════════════════════════════════════════
    # PAGE 3 — HR · Director · CEO
    # ═══════════════════════════════════════════════════════════════════════
    b.need(999)  # force page 3

    b.bar('UPPER HIERARCHY COMMENTS & SIGNATURES')

    b.comment_block(
        'HR MANAGER / RESP. RESSOURCES HUMAINES',
        rec.hr_comment, rec.hr_signed_by,
        rec.hr_signed_at, rec.hr_sig_b64)

    b.comment_block(
        'ADMINISTRATIVE DIRECTOR / DIRECTEUR ADMINISTRATIF',
        rec.director_comment, rec.director_signed_by,
        rec.director_signed_at, rec.director_sig_b64)

    b.comment_block(
        'CEO / DIRECTEUR GÉNÉRAL',
        rec.ceo_comment, rec.ceo_signed_by,
        rec.ceo_signed_at, rec.ceo_sig_b64)

    # Closing note
    b.need(8 * mm)
    b._text(
        'Appraisal feedback to be provided to staff by end of first month of next Trimester.',
        LM, b.y - 2 * mm, sz=7.5, col=NAVY)

    b._end_page()
    b.cv.save()
    buf.seek(0)
    return buf
