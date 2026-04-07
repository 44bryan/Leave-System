"""
Africa Eye Foundation — Personnel Appraisal PDF
2-page compact layout. Colors from logo only: teal + navy.
"""
from io import BytesIO
from datetime import date as _date
import os

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as _canvas
from reportlab.lib.utils import simpleSplit, ImageReader

W, H = A4   # 595 x 842 pt

# ── 2 colors from the logo ───────────────────────────────────────────────────
TEAL  = (0.176, 0.706, 0.784)   # #2DB5C8 — logo circle
NAVY  = (0.051, 0.420, 0.549)   # #0D6B8C — logo text
LTEAL = (0.90,  0.97,  0.98 )   # very light teal — alt rows
WHITE = (1.0,   1.0,   1.0  )
INK   = (0.10,  0.10,  0.10 )   # near-black for body text

LM = 10 * mm          # left margin
RM = W - 10 * mm
BM = 9  * mm          # bottom margin
CW = RM - LM          # content width = 175mm

# ── helpers ──────────────────────────────────────────────────────────────────

def _d(d):
    if d is None: return '—'
    if hasattr(d, 'date'): d = d.date()
    return d.strftime('%d/%m/%Y')

def _load_sig(b64):
    if not b64 or not b64.startswith('data:image/'): return None
    try:
        from PIL import Image as PI
        import io as _io, base64 as _b
        raw = _b.b64decode(b64.split(',', 1)[1])
        img = PI.open(_io.BytesIO(raw)); img.load()
        if img.mode in ('RGBA','LA','P'):
            bg = PI.new('RGBA', img.size, (255,255,255,255))
            bg.paste(img.convert('RGBA'), mask=img.convert('RGBA').split()[3])
            img = bg.convert('RGB')
        else:
            img = img.convert('RGB')
        out = _io.BytesIO(); img.save(out, 'PNG')
        return ImageReader(_io.BytesIO(out.getvalue()))
    except Exception:
        return None

def _logo():
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), 'static', 'LOGO.png')


# ── cursor-based builder ─────────────────────────────────────────────────────

class P:
    def __init__(self, buf):
        self.cv   = _canvas.Canvas(buf, pagesize=A4)
        self.y    = H
        self._pg  = 0

    # primitives
    def R(self, x, y_top, w, h, fill, stroke=None, lw=0.4):
        c = self.cv
        c.setFillColorRGB(*fill)
        if stroke:
            c.setStrokeColorRGB(*stroke); c.setLineWidth(lw)
            c.rect(x, y_top-h, w, h, fill=1, stroke=1)
        else:
            c.rect(x, y_top-h, w, h, fill=1, stroke=0)

    def T(self, s, x, y, font='Helvetica', sz=8, col=INK, align='L'):
        c = self.cv; c.setFillColorRGB(*col); c.setFont(font, sz)
        s = str(s)
        if   align == 'C': c.drawCentredString(x, y, s)
        elif align == 'R': c.drawRightString(x, y, s)
        else:               c.drawString(x, y, s)

    def lines(self, text, mw, font='Helvetica', sz=8):
        return simpleSplit(text or '—', font, sz, mw)

    def sig(self, b64, x, y_top, mw, mh):
        r = _load_sig(b64)
        if not r: return
        try: self.cv.drawImage(r, x, y_top-mh, width=mw, height=mh,
                               preserveAspectRatio=True, mask='auto')
        except Exception: pass

    def need(self, h, rec):
        if self.y - h < BM + 2*mm:
            self._end_page(rec)
            self._start_page(rec)

    # page management
    def _start_page(self, rec):
        self._pg += 1
        c = self.cv
        # teal top bar 12mm
        self.R(0, H, W, 12*mm, TEAL)
        # logo
        lp = _logo()
        if os.path.exists(lp):
            c.drawImage(lp, LM, H-12*mm+1*mm, width=38*mm, height=10*mm,
                        preserveAspectRatio=True, mask='auto')
        # title centred
        cx = LM + 42*mm + (CW - 42*mm)/2
        c.setFillColorRGB(*WHITE); c.setFont('Helvetica-Bold', 11)
        c.drawCentredString(cx, H-5*mm, 'PERSONNEL APPRAISAL  —  AFRICA EYE FOUNDATION')
        c.setFont('Helvetica', 7.5)
        c.drawCentredString(cx, H-9.5*mm,
            f'Cycle: Trimester {rec.cycle.trimester} · {rec.cycle.year}   |   Page {self._pg}')
        self.y = H - 14*mm

    def _end_page(self, rec):
        c = self.cv
        # footer line
        c.setStrokeColorRGB(*TEAL); c.setLineWidth(0.6)
        c.line(LM, BM-1*mm, RM, BM-1*mm)
        c.setFont('Helvetica', 6.5); c.setFillColorRGB(*NAVY)
        c.drawString(LM, BM-4*mm, 'AEF HRM · Africa Eye Foundation')
        c.drawRightString(RM, BM-4*mm, f'Generated: {_date.today().strftime("%d/%m/%Y")}')
        c.showPage()

    def bar(self, label, rec, h=5*mm):
        self.need(h+1*mm, rec)
        self.R(LM, self.y, CW, h, NAVY)
        self.T(label, LM+2.5*mm, self.y-h+1.5*mm, 'Helvetica-Bold', 7.5, WHITE)
        self.y -= h+0.5*mm

    def info2(self, ll, lv, rl, rv, bg=WHITE, rh=8.5*mm):
        hw = CW/2
        self.R(LM,     self.y, hw, rh, bg, NAVY, 0.3)
        self.R(LM+hw,  self.y, hw, rh, bg, NAVY, 0.3)
        self.T(ll, LM+1.5*mm,    self.y-2.5*mm, sz=6, col=NAVY)
        self.T(str(lv or'—'), LM+1.5*mm, self.y-6.5*mm, 'Helvetica-Bold', 8)
        self.T(rl, LM+hw+1.5*mm, self.y-2.5*mm, sz=6, col=NAVY)
        self.T(str(rv or'—'), LM+hw+1.5*mm, self.y-6.5*mm, 'Helvetica-Bold', 8)
        self.y -= rh

    def text_box(self, label, text, rec, max_lines=3):
        ls = self.lines(text, CW-4*mm, sz=8)[:max_lines]
        bh = max(7*mm, len(ls)*4.2*mm + 4*mm)
        self.need(4*mm+bh+0.5*mm, rec)
        self.R(LM, self.y, CW, 4*mm, LTEAL, NAVY, 0.3)
        self.T(label, LM+1.5*mm, self.y-2.8*mm, sz=6.5, col=NAVY)
        self.y -= 4*mm
        self.R(LM, self.y, CW, bh, WHITE, NAVY, 0.3)
        cy = self.y-3*mm
        for l in ls:
            self.T(l, LM+2*mm, cy, sz=8); cy -= 4.2*mm
        self.y -= bh+0.5*mm

    def rating_half(self, rows, vals, x, w, col_w=7*mm, rh=5*mm, hh=5*mm):
        """Draw rating table at arbitrary x without moving self.y. Returns bottom y."""
        lw = w - 5*col_w
        y  = self.y
        # header cols 1-5
        self.R(x, y, w, hh, NAVY)
        for i in range(5):
            cx = x + lw + i*col_w + col_w/2
            self.T(str(i+1), cx, y-hh+1.2*mm, 'Helvetica-Bold', 7, WHITE, 'C')
        y -= hh
        for idx,(field,label) in enumerate(rows):
            bg = LTEAL if idx%2 else WHITE
            self.R(x, y, w, rh, bg, NAVY, 0.25)
            disp = label[:30]+'…' if len(label)>30 else label
            self.T(disp, x+1.5*mm, y-rh+1.3*mm, sz=6.5)
            val = vals.get(field)
            cv  = self.cv
            for i in range(5):
                cx = x + lw + i*col_w + col_w/2
                cy = y - rh/2 - 0.3*mm
                r  = 1.7*mm
                cv.setStrokeColorRGB(*NAVY); cv.setLineWidth(0.35)
                cv.circle(cx, cy, r, fill=0, stroke=1)
                if val is not None and val == i+1:
                    cv.setFillColorRGB(*TEAL)
                    cv.circle(cx, cy, r-0.4, fill=1, stroke=0)
            y -= rh
        return y - 0.5*mm

    def two_rating_tables(self, left_rows, left_vals, right_rows, right_vals,
                          left_title, right_title, rec):
        half = CW/2 - 0.5*mm
        lh = 4*mm + 5*mm + len(left_rows)*5*mm + 0.5*mm
        rh = 4*mm + 5*mm + len(right_rows)*5*mm + 0.5*mm
        self.need(max(lh, rh)+1*mm, rec)
        # titles
        y0 = self.y
        self.T(left_title,  LM+1*mm,         y0-1.5*mm, 'Helvetica-Bold', 7, NAVY)
        self.T(right_title, LM+half+1.5*mm,  y0-1.5*mm, 'Helvetica-Bold', 7, NAVY)
        self.y -= 4*mm
        y_left  = self.rating_half(left_rows,  left_vals,  LM,           half)
        y_right = self.rating_half(right_rows, right_vals, LM+half+1*mm, half)
        self.y  = min(y_left, y_right) + 0.5*mm

    def sig_row(self, signed_by, signed_at, sig_b64, rec):
        """Compact name+date+sig strip — 14mm high."""
        SH = 14*mm
        self.need(SH+0.5*mm, rec)
        self.R(LM, self.y, CW, SH, LTEAL, NAVY, 0.3)
        name = signed_by.get_full_name() if signed_by else 'Pending'
        self.T('Name:',           LM+2*mm, self.y-3*mm,  sz=6, col=NAVY)
        self.T(name,              LM+2*mm, self.y-7.5*mm,'Helvetica-Bold', 8)
        self.T('Date:',           LM+2*mm, self.y-11*mm, sz=6, col=NAVY)
        self.T(_d(signed_at),     LM+11*mm,self.y-11*mm, sz=8)
        self.T('Signature:',      LM+CW*0.48, self.y-3*mm, sz=6, col=NAVY)
        self.sig(sig_b64 or '', LM+CW*0.48, self.y-2*mm, CW*0.49, SH-3*mm)
        self.y -= SH+0.5*mm

    def comment_block(self, title, comment, signed_by, signed_at, sig_b64, rec, max_lines=5):
        """Atomic: title bar + comment box + sig row. One need() for whole block."""
        ls   = self.lines(comment, CW-4*mm, sz=8)[:max_lines]
        cbh  = max(8*mm, len(ls)*4.2*mm + 4*mm)
        tot  = 5*mm + cbh + 14*mm + 1*mm
        self.need(tot, rec)
        # title bar
        self.R(LM, self.y, CW, 5*mm, NAVY)
        self.T(title, LM+2.5*mm, self.y-3.5*mm, 'Helvetica-Bold', 7.5, WHITE)
        self.y -= 5*mm
        # comment
        self.R(LM, self.y, CW, cbh, WHITE, NAVY, 0.3)
        cy = self.y-3*mm
        for l in ls:
            self.T(l, LM+2*mm, cy, sz=8); cy -= 4.2*mm
        self.y -= cbh
        # sig
        self.sig_row(signed_by, signed_at, sig_b64, rec)

    def total_table(self, rec, disc):
        """Total Ratings by Administration — compact."""
        has_ov = rec.has_score_override
        if has_ov:
            pf_s = f'{rec.final_performance_score} (sup:{rec.mgr_performance_score or"—"})'
            aa_s = f'{rec.final_attitude_score} (sup:{rec.mgr_attitude_score or"—"})'
        else:
            pf_s = str(rec.final_performance_score) if rec.final_performance_score is not None else '—'
            aa_s = str(rec.final_attitude_score)     if rec.final_attitude_score     is not None else '—'

        rows = [
            ('1','Performance Factors',           '12.5', pf_s),
            ('2','Attitude & Aptitude Factors',   '7.5',  aa_s),
            ('3','Discipline Sanctions (–1 each)','',     str(disc['deduction'])),
            ('4','Awards / Bonus (+1 each)',       '',     f'+{rec.award_bonus}'),
        ]
        rh = 6*mm
        tot = rh*(len(rows)+1)+1*mm
        self.need(tot, rec)
        sn=8*mm; mk=20*mm; sc=28*mm; cat=CW-sn-mk-sc
        # header
        self.R(LM, self.y, CW, rh, NAVY)
        self.T('SN',           LM+sn/2,         self.y-rh+2*mm,'Helvetica-Bold',7,WHITE,'C')
        self.T('Category',     LM+sn+1.5*mm,    self.y-rh+2*mm,'Helvetica-Bold',7,WHITE)
        self.T('Total Marks',  LM+sn+cat+mk/2,  self.y-rh+2*mm,'Helvetica-Bold',7,WHITE,'C')
        self.T('Score',        LM+sn+cat+mk+sc/2,self.y-rh+2*mm,'Helvetica-Bold',7,WHITE,'C')
        self.y -= rh
        for idx,(sno,cat_,mk_,sc_) in enumerate(rows):
            bg = LTEAL if idx%2 else WHITE
            self.R(LM, self.y, CW, rh, bg, NAVY, 0.3)
            self.T(sno,  LM+sn/2,          self.y-rh+2*mm, sz=8,col=INK,align='C')
            self.T(cat_, LM+sn+1.5*mm,     self.y-rh+2*mm, sz=8)
            self.T(mk_,  LM+sn+cat+mk/2,   self.y-rh+2*mm, sz=8,col=INK,align='C')
            self.T(sc_,  LM+sn+cat+mk+sc/2,self.y-rh+2*mm,'Helvetica-Bold',8,col=NAVY,align='C')
            self.y -= rh
        # total row
        self.R(LM, self.y, CW, rh+1*mm, TEAL)
        self.T('TOTAL', LM+sn+1.5*mm, self.y-rh+2*mm,'Helvetica-Bold',9,WHITE)
        self.T('20',    LM+sn+cat+mk/2,self.y-rh+2*mm,'Helvetica-Bold',9,WHITE,'C')
        ts = str(rec.total_score) if rec.total_score is not None else '—'
        self.T(ts, LM+sn+cat+mk+sc/2, self.y-rh+2*mm,'Helvetica-Bold',11,WHITE,'C')
        self.y -= rh+2*mm
        if has_ov and rec.score_override_by:
            self.T(f'* Modified by: {rec.score_override_by.get_full_name()}  ({_d(rec.score_override_at)})',
                   LM, self.y, sz=6.5, col=NAVY)
            self.y -= 4*mm


# ── field definitions ────────────────────────────────────────────────────────

PF = [('pf_quality_of_work','Quality of Work'),
      ('pf_quantity_of_work','Quantity of Work'),
      ('pf_knowledge_techniques','Knowledge of Techniques'),
      ('pf_ability_to_learn','Ability / Interest to Learn')]

AA = [('aa_motivation','Motivation and Initiative'),
      ('aa_attitude_colleagues','Attitude towards Colleagues'),
      ('aa_relations_patients','Relations with Patients'),
      ('aa_judgment_team','Judgment, Team Spirit & Discretion'),
      ('aa_punctuality','Punctuality, Attendance & Honesty'),
      ('aa_presentation','Personal Presentation & Professionalism')]

MGR_PF = [(f'mgr_{f}',l) for f,l in PF]
MGR_AA = [(f'mgr_{f}',l) for f,l in AA]


# ── main ─────────────────────────────────────────────────────────────────────

def generate_appraisal_pdf(record):
    buf = BytesIO()
    b   = P(buf)
    rec = record
    emp = record.employee
    disc = record.discipline_deductions()

    # ── PAGE 1 ───────────────────────────────────────────────────────────────
    b._start_page(rec)

    # Employee info (3 rows)
    b.bar('EMPLOYEE INFORMATION', rec)
    b.info2('Name / Nom',         emp.user.get_full_name(),
            'Position / Poste',   emp.position or '—')
    b.info2('Department',         str(emp.department or '—'),
            'Date Hired',         _d(emp.date_joined_company), bg=LTEAL)
    b.info2('Period',             rec.cycle.get_trimester_dates(),
            'Year',               str(rec.cycle.year))
    b.y -= 1*mm

    # Tasks
    b.bar('1 & 2.  JOB IDENTIFICATION & TASKS', rec)
    b.text_box('Summary of main job attributions / tasks:', rec.tasks_summary, rec, max_lines=3)
    b.text_box('Tasks assimilated by the employee:',        rec.tasks_assimilated, rec, max_lines=2)

    # Mastery legend
    b.need(4*mm, rec)
    b.T('Mastery: 1=Does not meet  2=Some difficulties  3=Meets requirements  4=Exceeds  5=Greatly exceeds',
        LM, b.y-1.5*mm, sz=6, col=NAVY)
    b.y -= 4*mm

    # Section 3: Appraisee self-rating
    b.bar('3.  APPRAISEE SELF-RATING  (Employee)', rec)
    self_pf = {f: getattr(rec,f) for f,_ in PF}
    self_aa = {f: getattr(rec,f) for f,_ in AA}
    b.two_rating_tables(PF, self_pf, AA, self_aa,
                        'Performance Factors', 'Attitude & Aptitude Factors', rec)

    # Section 4: Appraiser rating (supervisor)
    b.bar('4.  APPRAISER RATING  (Supervisor / Line Manager)', rec)
    mgr_pf = {f: getattr(rec,f) for f,_ in MGR_PF}
    mgr_aa = {f: getattr(rec,f) for f,_ in MGR_AA}
    b.two_rating_tables(MGR_PF, mgr_pf, MGR_AA, mgr_aa,
                        'Performance Factors', 'Attitude & Aptitude Factors', rec)

    # Goals
    b.bar('5.  GOALS TO REACH', rec)
    b.text_box('Goals / Action Points:', rec.goals_to_reach, rec, max_lines=2)

    # Discipline
    b.bar('6.  DISCIPLINARY SANCTIONS  (–1 per sanction)', rec)
    sanctions = [
        ('verbal_warning',  'Verbal Warning'),
        ('written_caution', 'Written Caution / Request for Explanation'),
        ('final_warning',   'Written Warning / Final Written Warning'),
        ('suspension',      'Written Reprimand / Suspension'),
        ('dismissal',       'Dismissal'),
    ]
    rh = 5*mm
    col_y = CW*0.73; col_n = CW*0.86
    b.need((len(sanctions)+2)*rh, rec)
    # header
    b.R(LM, b.y, CW, rh, NAVY)
    b.T('Sanction Type', LM+1.5*mm, b.y-rh+1.5*mm, 'Helvetica-Bold', 7, WHITE)
    b.T('YES', LM+col_y+CW*0.065, b.y-rh+1.5*mm, 'Helvetica-Bold', 7, WHITE, 'C')
    b.T('NO',  LM+col_n+CW*0.07,  b.y-rh+1.5*mm, 'Helvetica-Bold', 7, WHITE, 'C')
    b.y -= rh
    for idx,(key,label) in enumerate(sanctions):
        bg = LTEAL if idx%2 else WHITE
        b.R(LM, b.y, CW, rh, bg, NAVY, 0.25)
        b.T(label, LM+1.5*mm, b.y-rh+1.5*mm, sz=7)
        cy = b.y-rh/2-0.5*mm
        count = disc['counts'].get(key,0)
        if count: b.T('✓', LM+col_y+CW*0.065, cy, 'Helvetica-Bold', 9, TEAL, 'C')
        else:     b.T('✓', LM+col_n+CW*0.07,  cy, 'Helvetica-Bold', 9, NAVY, 'C')
        b.y -= rh
    b.R(LM, b.y, CW, rh, LTEAL, NAVY, 0.3)
    b.T('Total Deduction:', LM+1.5*mm, b.y-rh+1.5*mm, 'Helvetica-Bold', 7, NAVY)
    col = TEAL if disc['deduction']<0 else NAVY
    b.T(str(disc['deduction']), LM+col_y-6*mm, b.y-rh+1.5*mm, 'Helvetica-Bold', 9, col)
    b.y -= rh+1*mm

    # Awards
    b.bar('7.  AWARDS RECEIVED  (+1 per award)', rec)
    awards = [('Employee of the Month', rec.award_employee_of_month),
              (f'Other: {rec.award_other or"—"}', bool(rec.award_other))]
    b.need((len(awards)+1)*rh, rec)
    b.R(LM, b.y, CW, rh, NAVY)
    b.T('Award', LM+1.5*mm, b.y-rh+1.5*mm, 'Helvetica-Bold', 7, WHITE)
    b.T('YES', LM+col_y+CW*0.065, b.y-rh+1.5*mm, 'Helvetica-Bold', 7, WHITE, 'C')
    b.T('NO',  LM+col_n+CW*0.07,  b.y-rh+1.5*mm, 'Helvetica-Bold', 7, WHITE, 'C')
    b.y -= rh
    for idx,(label,has_it) in enumerate(awards):
        bg = LTEAL if idx%2 else WHITE
        b.R(LM, b.y, CW, rh, bg, NAVY, 0.25)
        b.T(label, LM+1.5*mm, b.y-rh+1.5*mm, sz=7)
        cy = b.y-rh/2-0.5*mm
        if has_it: b.T('✓', LM+col_y+CW*0.065, cy, 'Helvetica-Bold', 9, TEAL, 'C')
        else:      b.T('✓', LM+col_n+CW*0.07,  cy, 'Helvetica-Bold', 9, NAVY, 'C')
        b.y -= rh
    b.y -= 1*mm

    # ── PAGE 2 ───────────────────────────────────────────────────────────────
    b._end_page(rec)
    b._start_page(rec)

    # Section 8: Employee comments
    b.bar('8.  EMPLOYEE COMMENTS & SIGNATURE', rec)
    col3 = CW/3
    b.need(5*mm+13*mm+14*mm+1*mm, rec)
    # 3 comment mini-boxes side by side
    for i,(lbl,val) in enumerate([
        ('Comment on Self',        rec.comment_on_self),
        ('Comment on Supervision', rec.comment_on_supervision),
        ('Comment on Organisation',rec.comment_on_org),
    ]):
        x = LM+i*col3
        b.R(x, b.y, col3, 4.5*mm, NAVY)
        b.T(lbl, x+1*mm, b.y-3.2*mm, sz=6.5, col=WHITE)
    b.y -= 4.5*mm
    ch = 11*mm
    for i,(_,val) in enumerate([('',rec.comment_on_self),
                                  ('',rec.comment_on_supervision),
                                  ('',rec.comment_on_org)]):
        x = LM+i*col3
        b.R(x, b.y, col3, ch, WHITE, NAVY, 0.3)
        ls = b.lines(val, col3-3*mm, sz=7.5)[:2]
        cy = b.y-3*mm
        for l in ls: b.T(l, x+1.5*mm, cy, sz=7.5); cy -= 4*mm
    b.y -= ch
    b.sig_row(rec.employee, rec.employee_signed_at, rec.employee_sig_b64, rec)

    # Co-worker
    b.comment_block('CO-WORKER / COLLÈGUE',
                    rec.coworker_comment, rec.coworker_signed_by,
                    rec.coworker_signed_at, rec.coworker_sig_b64, rec)

    # Supervisor comment
    b.comment_block('SUPERVISOR COMMENT & SIGNATURE',
                    rec.unit_head_comment, rec.unit_head_signed_by,
                    rec.unit_head_signed_at, rec.unit_head_sig_b64, rec)

    # Total Ratings
    b.bar('TOTAL RATINGS BY ADMINISTRATION', rec)
    b.total_table(rec, disc)

    # HR
    b.comment_block('HR MANAGER / RESP. RESSOURCES HUMAINES',
                    rec.hr_comment, rec.hr_signed_by,
                    rec.hr_signed_at, rec.hr_sig_b64, rec)

    # Director
    b.comment_block('ADMINISTRATIVE DIRECTOR / DIRECTEUR ADMINISTRATIF',
                    rec.director_comment, rec.director_signed_by,
                    rec.director_signed_at, rec.director_sig_b64, rec)

    # CEO
    b.comment_block('CEO / DIRECTEUR GÉNÉRAL',
                    rec.ceo_comment, rec.ceo_signed_by,
                    rec.ceo_signed_at, rec.ceo_sig_b64, rec)

    # closing note
    b.need(6*mm, rec)
    b.T('Appraisal feedback to be provided to staff by end of first month of next Trimester.',
        LM, b.y-2*mm, sz=6.5, col=NAVY)

    b._end_page(rec)
    b.cv.save()
    buf.seek(0)
    return buf
