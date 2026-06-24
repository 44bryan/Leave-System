"""
Africa Eye Foundation — Personnel Appraisal PDF
Colors match the leave-system PDF. Signatures always rendered.
"""
from io import BytesIO
from datetime import date as _date
import os, io as _io, base64 as _b64

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas as _canvas
from reportlab.lib.utils import simpleSplit, ImageReader

W, H = A4   # 595 × 842 pt

# ── Colours — match leave-system PDF exactly ────────────────────────────────
CYAN  = (0.192, 0.722, 0.812)   # #31b8cf  bars / headers / lines
BLUE  = (0.141, 0.588, 0.729)   # #2496ba  title text
DARK  = (0.024, 0.098, 0.118)   # #06191e  body text
LABEL = (0.086, 0.325, 0.365)   # #16535d  field labels
BORD  = (0.700, 0.850, 0.900)   # #b3d9e6  cell borders
LCYAN = (0.906, 0.965, 0.980)   # very light cyan  alt rows
WHITE = (1.0, 1.0, 1.0)

LM = 12 * mm
RM = W - 12 * mm
CW = RM - LM
BM = 10 * mm

HEADER_H = 22 * mm
FOOTER_H =  8 * mm


# ── helpers ──────────────────────────────────────────────────────────────────

def _d(v):
    if v is None: return '—'
    if hasattr(v, 'date'): v = v.date()
    return v.strftime('%d/%m/%Y')


def _pil_to_reader(pil_img):
    """Flatten any PIL image to RGB and return a ReportLab ImageReader."""
    from PIL import Image as _PI
    if pil_img.mode in ('RGBA', 'LA', 'P'):
        rgba = pil_img.convert('RGBA')
        bg   = _PI.new('RGBA', rgba.size, (255, 255, 255, 255))
        bg.paste(rgba, mask=rgba.split()[3])
        pil_img = bg.convert('RGB')
    else:
        pil_img = pil_img.convert('RGB')
    out = _io.BytesIO()
    pil_img.save(out, format='PNG')
    return ImageReader(_io.BytesIO(out.getvalue()))


def _load_sig(b64):
    """Return a ReportLab ImageReader from a data-URI base64 signature, or None.
    Always routes through Pillow so RGBA/transparent PNGs are composited on white."""
    if not b64 or not b64.startswith('data:image/'):
        return None
    try:
        from PIL import Image as _PI
        raw     = _b64.b64decode(b64.split(',', 1)[1])
        pil_img = _PI.open(_io.BytesIO(raw))
        pil_img.load()
        return _pil_to_reader(pil_img)
    except Exception:
        return None


def _logo_path():
    return os.path.join(
        os.path.dirname(os.path.dirname(__file__)), 'static', 'LOGO.png'
    )


# ── Builder ──────────────────────────────────────────────────────────────────

class Builder:
    """
    y always points to the TOP of the next element to draw.
    Every draw call moves y down. need(h) inserts a page break if h won't fit.
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
            c.setStrokeColorRGB(*stroke)
            c.setLineWidth(lw)
            c.rect(x, y_top - h, w, h, fill=1, stroke=1)
        else:
            c.rect(x, y_top - h, w, h, fill=1, stroke=0)

    def _text(self, s, x, y, font='Helvetica', sz=8.5, col=DARK, align='L'):
        c = self.cv
        c.setFillColorRGB(*col)
        c.setFont(font, sz)
        s = str(s)
        if   align == 'C': c.drawCentredString(x, y, s)
        elif align == 'R': c.drawRightString(x, y, s)
        else:               c.drawString(x, y, s)

    def _wrap(self, text, max_w, font='Helvetica', sz=8.5):
        return simpleSplit(text or '', font, sz, max_w)

    def _sig_img(self, b64, x, y_top, mw, mh):
        r = _load_sig(b64)
        if not r:
            return False
        try:
            self.cv.drawImage(r, x, y_top - mh, width=mw, height=mh,
                              preserveAspectRatio=True)
            return True
        except Exception:
            return False

    def _render_sig(self, sig_b64, signed_by, x, y_top, mw, mh):
        """Draw signature image. If sig_b64 is absent, show (not signed) — should not happen
        for submitted appraisals since the form enforces signing before submission."""
        if sig_b64:
            self._sig_img(sig_b64, x, y_top, mw, mh)
        else:
            self._text('(not signed)', x, y_top - mh * 0.55, sz=7.5, col=BORD)

    # ── page management ──────────────────────────────────────────────────────

    def _new_page(self):
        rec = self.rec
        self._pg += 1
        c = self.cv

        # White header
        self._rect(0, H, W, HEADER_H, WHITE)

        # Logo on white
        lp = _logo_path()
        if os.path.exists(lp):
            c.drawImage(lp, LM, H - HEADER_H + 3 * mm,
                        width=46 * mm, height=16 * mm,
                        preserveAspectRatio=True, mask='auto')

        # Title — right of logo
        c.setFont('Helvetica-Bold', 13)
        c.setFillColorRGB(*BLUE)
        c.drawString(LM + 50 * mm, H - 9 * mm, 'PERSONNEL APPRAISAL')

        # Cycle + page — top right
        c.setFont('Helvetica', 7.5)
        c.setFillColorRGB(*LABEL)
        c.drawRightString(RM, H - 8  * mm, f'Trimester {rec.cycle.trimester}  ·  {rec.cycle.year}')
        c.drawRightString(RM, H - 14 * mm, f'Page {self._pg}')

        # Cyan line under header
        c.setStrokeColorRGB(*CYAN)
        c.setLineWidth(2.0)
        c.line(0, H - HEADER_H, W, H - HEADER_H)

        self.y = H - HEADER_H - 3 * mm

    def _end_page(self):
        rec = self.rec
        c   = self.cv
        c.setStrokeColorRGB(*CYAN)
        c.setLineWidth(1.0)
        c.line(0, FOOTER_H, W, FOOTER_H)
        c.setFont('Helvetica', 6.5)
        c.setFillColorRGB(*LABEL)
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
        self.need(h + 2 * mm)
        self._rect(LM, self.y, CW, h, CYAN)
        self._text(label, LM + 3 * mm, self.y - h + 2 * mm,
                   'Helvetica-Bold', 8, WHITE)
        self.y -= h + 1 * mm

    # ── two-column info row ───────────────────────────────────────────────────

    def info_row(self, ll, lv, rl, rv, shade=False):
        rh  = 9 * mm
        hw  = CW / 2
        bg  = LCYAN if shade else WHITE
        self._rect(LM,      self.y, hw, rh, bg, BORD, 0.4)
        self._rect(LM + hw, self.y, hw, rh, bg, BORD, 0.4)
        self._text(ll, LM + 2 * mm,      self.y - 2.5 * mm, sz=6.5, col=LABEL)
        self._text(str(lv or '—'), LM + 2 * mm, self.y - 7 * mm,
                   'Helvetica-Bold', 9, DARK)
        self._text(rl, LM + hw + 2 * mm, self.y - 2.5 * mm, sz=6.5, col=LABEL)
        self._text(str(rv or '—'), LM + hw + 2 * mm, self.y - 7 * mm,
                   'Helvetica-Bold', 9, DARK)
        self.y -= rh

    # ── text content box ──────────────────────────────────────────────────────

    def text_box(self, label, text, max_lines=4):
        LH  = 4.5 * mm
        ls  = self._wrap(text, CW - 5 * mm)[:max_lines]
        bh  = max(9 * mm, len(ls) * LH + 5 * mm)
        self.need(5 * mm + bh + 1 * mm)
        self._rect(LM, self.y, CW, 5 * mm, LCYAN, BORD, 0.4)
        self._text(label, LM + 2 * mm, self.y - 3.5 * mm, sz=7, col=LABEL)
        self.y -= 5 * mm
        self._rect(LM, self.y, CW, bh, WHITE, BORD, 0.4)
        cy = self.y - 3.5 * mm
        for ln in ls:
            self._text(ln, LM + 2.5 * mm, cy, sz=8.5, col=DARK)
            cy -= LH
        self.y -= bh + 1 * mm

    # ── rating table (half-width, does NOT touch self.y) ─────────────────────

    def _rating_table_at(self, rows, vals, x, w, y_top):
        col_w = 7.5 * mm
        lbl_w = w - 5 * col_w
        HDR   = 5.5 * mm
        ROW   = 5.5 * mm
        y     = y_top

        self._rect(x, y, w, HDR, CYAN)
        for i in range(5):
            cx = x + lbl_w + i * col_w + col_w / 2
            self._text(str(i + 1), cx, y - HDR + 1.5 * mm,
                       'Helvetica-Bold', 7.5, WHITE, 'C')
        y -= HDR

        for idx, (field, label) in enumerate(rows):
            bg = LCYAN if idx % 2 else WHITE
            self._rect(x, y, w, ROW, bg, BORD, 0.3)
            disp = label if len(label) <= 32 else label[:29] + '…'
            self._text(disp, x + 1.5 * mm, y - ROW + 1.5 * mm, sz=7, col=DARK)
            val = vals.get(field)
            c   = self.cv
            for i in range(5):
                cx  = x + lbl_w + i * col_w + col_w / 2
                cy  = y - ROW / 2 - 0.5 * mm
                rad = 1.9 * mm
                c.setStrokeColorRGB(*CYAN)
                c.setLineWidth(0.4)
                c.circle(cx, cy, rad, fill=0, stroke=1)
                if val is not None and val == i + 1:
                    c.setFillColorRGB(*CYAN)
                    c.circle(cx, cy, rad - 0.4, fill=1, stroke=0)
            y -= ROW
        return y - 1 * mm

    def two_tables(self, left_rows, left_vals, right_rows, right_vals,
                   left_title, right_title):
        half  = CW / 2 - 1 * mm
        lh = 4 * mm + 5.5 * mm + len(left_rows)  * 5.5 * mm + 1 * mm
        rh = 4 * mm + 5.5 * mm + len(right_rows) * 5.5 * mm + 1 * mm
        self.need(max(lh, rh))

        y0 = self.y
        self._text(left_title,  LM + 1 * mm,                  y0 - 1.5 * mm, 'Helvetica-Bold', 7.5, LABEL)
        self._text(right_title, LM + half + 2 * mm + 1 * mm,  y0 - 1.5 * mm, 'Helvetica-Bold', 7.5, LABEL)
        y_start = y0 - 4 * mm

        y_l = self._rating_table_at(left_rows,  left_vals,  LM,                 half, y_start)
        y_r = self._rating_table_at(right_rows, right_vals, LM + half + 2 * mm, half, y_start)
        self.y = min(y_l, y_r)

    # ── signature strip ───────────────────────────────────────────────────────

    def sig_strip(self, signed_by, signed_at, sig_b64):
        SH = 16 * mm
        self.need(SH + 1 * mm)
        y = self.y
        self._rect(LM, y, CW, SH, LCYAN, BORD, 0.4)

        name = signed_by.get_full_name() if signed_by else 'Pending / Not yet signed'
        self._text('Name:',       LM + 2 * mm, y - 3   * mm, sz=6.5, col=LABEL)
        self._text(name,          LM + 2 * mm, y - 8   * mm, 'Helvetica-Bold', 9, DARK)
        self._text('Date:',       LM + 2 * mm, y - 13  * mm, sz=6.5, col=LABEL)
        self._text(_d(signed_at), LM + 12 * mm,y - 13  * mm, sz=8.5, col=DARK)

        sig_x = LM + CW * 0.47
        self._text('Signature:', sig_x, y - 3 * mm, sz=6.5, col=LABEL)
        self._render_sig(sig_b64, signed_by, sig_x + 1 * mm, y - 4 * mm, CW * 0.50, SH - 5 * mm)

        self.y = y - SH - 1 * mm

    # ── comment + signature block (fully atomic) ──────────────────────────────

    def comment_block(self, title, comment, signed_by, signed_at, sig_b64,
                      max_lines=6):
        LH  = 4.5 * mm
        BAR = 6   * mm
        SIG = 16  * mm

        lines = self._wrap(comment, CW - 5 * mm)[:max_lines]
        cbh   = max(10 * mm, len(lines) * LH + 5 * mm)
        total = BAR + cbh + SIG + 2 * mm

        self.need(total)
        y = self.y

        # bar
        self._rect(LM, y, CW, BAR, CYAN)
        self._text(title, LM + 3 * mm, y - BAR + 2 * mm, 'Helvetica-Bold', 8, WHITE)
        y -= BAR

        # comment body
        self._rect(LM, y, CW, cbh, WHITE, BORD, 0.4)
        cy = y - 3.5 * mm
        for ln in lines:
            self._text(ln, LM + 2.5 * mm, cy, sz=8.5, col=DARK)
            cy -= LH
        y -= cbh

        # sig strip
        self._rect(LM, y, CW, SIG, LCYAN, BORD, 0.4)
        name = signed_by.get_full_name() if signed_by else 'Pending / Not yet signed'
        self._text('Name:',       LM + 2 * mm, y - 3   * mm, sz=6.5, col=LABEL)
        self._text(name,          LM + 2 * mm, y - 8   * mm, 'Helvetica-Bold', 9, DARK)
        self._text('Date:',       LM + 2 * mm, y - 13  * mm, sz=6.5, col=LABEL)
        self._text(_d(signed_at), LM + 12 * mm,y - 13  * mm, sz=8.5, col=DARK)
        sig_x = LM + CW * 0.47
        self._text('Signature:', sig_x, y - 3 * mm, sz=6.5, col=LABEL)
        self._render_sig(sig_b64, signed_by, sig_x + 1 * mm, y - 4 * mm, CW * 0.50, SIG - 5 * mm)
        y -= SIG

        self.y = y - 2 * mm

    # ── score modification table ──────────────────────────────────────────────

    def override_diff_table(self):
        """Show full score modification chain — only rendered when at least one role changed a score."""
        rec  = self.rec
        rows = rec.score_changes_display()
        if not rows:
            return

        AMBER      = (0.984, 0.753, 0.176)
        AMBER_TEXT = (0.573, 0.247, 0.000)
        RH  = 6.5 * mm
        HDR = 6   * mm

        # Decide which columns to show (only include roles that made changes)
        show_hr  = rec.score_modified_by_hr is not None
        show_dir = rec.score_modified_by_director is not None
        show_ceo = rec.score_modified_by_ceo is not None

        n_mod_cols = sum([show_hr, show_dir, show_ceo])
        lbl_w  = CW * (0.40 if n_mod_cols >= 3 else 0.44 if n_mod_cols == 2 else 0.50)
        sup_w  = CW * 0.12
        mod_w  = (CW - lbl_w - sup_w) / max(n_mod_cols, 1) if n_mod_cols else 0
        fin_w  = CW * 0.12

        total_h = HDR + RH + len(rows) * RH + 10 * mm
        self.need(total_h)
        y = self.y

        # Header bar
        self._rect(LM, y, CW, HDR, AMBER)
        self._text('SCORE MODIFICATION AUDIT TRAIL  (Supervisor Original → Final)',
                   LM + 3 * mm, y - HDR + 1.5 * mm, 'Helvetica-Bold', 8, AMBER_TEXT)
        y -= HDR

        # Column headers
        self._rect(LM, y, CW, RH, LCYAN, BORD, 0.3)
        x = LM
        self._text('Factor',     x + 2 * mm, y - RH + 2 * mm, 'Helvetica-Bold', 7, LABEL)
        x += lbl_w
        self._text('Supervisor', x + sup_w / 2, y - RH + 2 * mm, 'Helvetica-Bold', 7, LABEL, 'C')
        x += sup_w
        if show_hr:
            by = rec.score_modified_by_hr
            lbl = f'HR ({by.user.last_name if by else ""})' if by else 'HR'
            self._text(lbl, x + mod_w / 2, y - RH + 2 * mm, 'Helvetica-Bold', 6.5, LABEL, 'C')
            x += mod_w
        if show_dir:
            by = rec.score_modified_by_director
            lbl = f'Director ({by.user.last_name if by else ""})' if by else 'Director'
            self._text(lbl, x + mod_w / 2, y - RH + 2 * mm, 'Helvetica-Bold', 6.5, LABEL, 'C')
            x += mod_w
        if show_ceo:
            by = rec.score_modified_by_ceo
            lbl = f'CEO ({by.user.last_name if by else ""})' if by else 'CEO'
            self._text(lbl, x + mod_w / 2, y - RH + 2 * mm, 'Helvetica-Bold', 6.5, LABEL, 'C')
            x += mod_w
        self._text('Final', x + (CW - (x - LM)) / 2, y - RH + 2 * mm, 'Helvetica-Bold', 7, BLUE, 'C')
        y -= RH

        for idx, row in enumerate(rows):
            bg = LCYAN if idx % 2 else WHITE
            self._rect(LM, y, CW, RH, bg, BORD, 0.3)
            x = LM
            disp = row['label'] if len(row['label']) <= 34 else row['label'][:31] + '…'
            self._text(disp, x + 2 * mm, y - RH + 2 * mm, sz=7, col=DARK)
            x += lbl_w
            self._text(str(row['supervisor'] or '—'), x + sup_w / 2, y - RH + 2 * mm, sz=8, col=LABEL, align='C')
            x += sup_w
            if show_hr:
                v = row['hr']
                self._text(str(v) if v else '—', x + mod_w / 2, y - RH + 2 * mm,
                           'Helvetica-Bold' if v else 'Helvetica', 8, CYAN if v else LABEL, 'C')
                x += mod_w
            if show_dir:
                v = row['director']
                self._text(str(v) if v else '—', x + mod_w / 2, y - RH + 2 * mm,
                           'Helvetica-Bold' if v else 'Helvetica', 8, CYAN if v else LABEL, 'C')
                x += mod_w
            if show_ceo:
                v = row['ceo']
                self._text(str(v) if v else '—', x + mod_w / 2, y - RH + 2 * mm,
                           'Helvetica-Bold' if v else 'Helvetica', 8, CYAN if v else LABEL, 'C')
                x += mod_w
            fin_x = LM + CW - (CW - (x - LM))
            self._text(str(row['final'] or '—'), fin_x + (CW - (x - LM)) / 2, y - RH + 2 * mm,
                       'Helvetica-Bold', 9, BLUE, 'C')
            y -= RH

        # Footer attribution line
        parts = []
        if rec.score_modified_by_hr:
            parts.append(f"HR: {rec.score_modified_by_hr.get_full_name()}  ({_d(rec.score_modified_at_hr)})")
        if rec.score_modified_by_director:
            parts.append(f"Director: {rec.score_modified_by_director.get_full_name()}  ({_d(rec.score_modified_at_director)})")
        if rec.score_modified_by_ceo:
            parts.append(f"CEO: {rec.score_modified_by_ceo.get_full_name()}  ({_d(rec.score_modified_at_ceo)})")
        if parts:
            self._text('Modified by:  ' + '   ·   '.join(parts), LM + 1 * mm, y - 2.5 * mm, sz=6.5, col=LABEL)
            y -= 5 * mm

        self.y = y - 1 * mm

    # ── independent scores comparison table ───────────────────────────────────

    def ind_scores_table(self):
        """Comparative independent scores — Manager, HR, Admin Director, CEO."""
        rec = self.rec
        INDIGO  = (0.298, 0.137, 0.569)
        LINDIGO = (0.937, 0.929, 0.980)

        all_factors = PF_ROWS + AA_ROWS
        rows_data = [{
            'label':    label,
            'manager':  getattr(rec, f'mgr_{fname}'),
            'hr':       getattr(rec, f'hr_ind_{fname}'),
            'director': getattr(rec, f'dir_ind_{fname}'),
            'ceo':      getattr(rec, f'ceo_ind_{fname}'),
        } for fname, label in all_factors]

        show_hr  = any(r['hr']       is not None for r in rows_data)
        show_dir = any(r['director'] is not None for r in rows_data)
        show_ceo = any(r['ceo']      is not None for r in rows_data)

        if not (show_hr or show_dir or show_ceo):
            return

        n_score_cols = 1 + sum([show_hr, show_dir, show_ceo])
        RH      = 6.5 * mm
        HDR     = 6   * mm
        lbl_w   = CW * 0.42
        score_w = (CW - lbl_w) / n_score_cols

        self.need(HDR + RH + len(rows_data) * RH + RH + 8 * mm)
        y = self.y

        # Header bar
        self._rect(LM, y, CW, HDR, INDIGO)
        self._text('INDEPENDENT SCORES BY REVIEWER LEVEL',
                   LM + 3 * mm, y - HDR + 1.5 * mm, 'Helvetica-Bold', 8, WHITE)
        y -= HDR

        # Column headers
        self._rect(LM, y, CW, RH, LCYAN, BORD, 0.3)
        x = LM
        self._text('Factor', x + 2 * mm, y - RH + 2 * mm, 'Helvetica-Bold', 7, LABEL)
        x += lbl_w
        self._text('Manager', x + score_w / 2, y - RH + 2 * mm, 'Helvetica-Bold', 7, LABEL, 'C')
        x += score_w
        if show_hr:
            self._text('HR Mgr', x + score_w / 2, y - RH + 2 * mm, 'Helvetica-Bold', 7, LABEL, 'C')
            x += score_w
        if show_dir:
            self._text('Admin Dir.', x + score_w / 2, y - RH + 2 * mm, 'Helvetica-Bold', 7, LABEL, 'C')
            x += score_w
        if show_ceo:
            self._text('CEO', x + score_w / 2, y - RH + 2 * mm, 'Helvetica-Bold', 7, LABEL, 'C')
        y -= RH

        # Data rows
        for idx, row in enumerate(rows_data):
            bg = LINDIGO if idx % 2 else WHITE
            self._rect(LM, y, CW, RH, bg, BORD, 0.3)
            x = LM
            disp = row['label'] if len(row['label']) <= 36 else row['label'][:33] + '…'
            self._text(disp, x + 2 * mm, y - RH + 2 * mm, sz=7, col=DARK)
            x += lbl_w

            def _cell(val, xp, _y=y, _sw=score_w):
                s   = str(val) if val is not None else '—'
                col = INDIGO if val is not None else LABEL
                fn  = 'Helvetica-Bold' if val is not None else 'Helvetica'
                self._text(s, xp + _sw / 2, _y - RH + 2 * mm, fn, 9, col, 'C')

            _cell(row['manager'],  x); x += score_w
            if show_hr:  _cell(row['hr'],       x); x += score_w
            if show_dir: _cell(row['director'],  x); x += score_w
            if show_ceo: _cell(row['ceo'],       x)
            y -= RH

        # Totals row (combined score)
        self._rect(LM, y, CW, RH, LCYAN, BORD, 0.4)
        self._text('Score  (PF /12.5 + AA /7.5):', LM + 2 * mm, y - RH + 2 * mm,
                   'Helvetica-Bold', 7.5, LABEL)
        x = LM + lbl_w

        def _tot(pf_s, aa_s):
            if pf_s is None or aa_s is None:
                return '—'
            return f'{round(pf_s + aa_s, 1)}'

        self._text(_tot(rec.mgr_performance_score, rec.mgr_attitude_score),
                   x + score_w / 2, y - RH + 2 * mm, 'Helvetica-Bold', 9, INDIGO, 'C'); x += score_w
        if show_hr:
            self._text(_tot(rec._ind_pf_score('hr_ind'), rec._ind_aa_score('hr_ind')),
                       x + score_w / 2, y - RH + 2 * mm, 'Helvetica-Bold', 9, INDIGO, 'C'); x += score_w
        if show_dir:
            self._text(_tot(rec._ind_pf_score('dir_ind'), rec._ind_aa_score('dir_ind')),
                       x + score_w / 2, y - RH + 2 * mm, 'Helvetica-Bold', 9, INDIGO, 'C'); x += score_w
        if show_ceo:
            self._text(_tot(rec._ind_pf_score('ceo_ind'), rec._ind_aa_score('ceo_ind')),
                       x + score_w / 2, y - RH + 2 * mm, 'Helvetica-Bold', 9, INDIGO, 'C')
        y -= RH

        self.y = y - 3 * mm

    # ── total ratings table ───────────────────────────────────────────────────

    def total_table(self, disc):
        rec    = self.rec
        has_ov = rec.has_score_override
        pf_s   = str(rec.final_performance_score) if rec.final_performance_score is not None else '—'
        aa_s   = str(rec.final_attitude_score)     if rec.final_attitude_score     is not None else '—'
        if has_ov:
            pf_s += ' *'
            aa_s += ' *'

        rows = [
            ('1', 'Performance Factors',            '12.5', pf_s),
            ('2', 'Attitude and Aptitude Factors',  '7.5',  aa_s),
            ('3', 'Discipline Sanctions (–1 each)', '',     str(disc['deduction'])),
            ('4', 'Awards / Bonus Points',          '',     f'+{rec.award_bonus_points}'),
        ]
        ROW = 7 * mm
        sn  = 9  * mm
        mk  = 22 * mm
        sc  = 28 * mm
        cat = CW - sn - mk - sc

        self.need(ROW * (len(rows) + 2) + 3 * mm)
        y = self.y

        # header
        self._rect(LM, y, CW, ROW, CYAN)
        self._text('SN',           LM + sn / 2,             y - ROW + 2.5 * mm, 'Helvetica-Bold', 8, WHITE, 'C')
        self._text('Category',     LM + sn + 2 * mm,        y - ROW + 2.5 * mm, 'Helvetica-Bold', 8, WHITE)
        self._text('Total Marks',  LM + sn + cat + mk / 2,  y - ROW + 2.5 * mm, 'Helvetica-Bold', 8, WHITE, 'C')
        self._text('Score',        LM + sn + cat + mk + sc / 2, y - ROW + 2.5 * mm, 'Helvetica-Bold', 8, WHITE, 'C')
        y -= ROW

        for idx, (sno, cat_, mk_, sc_) in enumerate(rows):
            bg = LCYAN if idx % 2 else WHITE
            self._rect(LM, y, CW, ROW, bg, BORD, 0.3)
            self._text(sno,  LM + sn / 2,              y - ROW + 2.5 * mm, sz=8.5, col=DARK, align='C')
            self._text(cat_, LM + sn + 2 * mm,         y - ROW + 2.5 * mm, sz=8.5, col=DARK)
            self._text(mk_,  LM + sn + cat + mk / 2,   y - ROW + 2.5 * mm, sz=8.5, col=DARK, align='C')
            self._text(sc_,  LM + sn + cat + mk + sc / 2, y - ROW + 2.5 * mm,
                       'Helvetica-Bold', 8.5, BLUE, 'C')
            y -= ROW

        # total row
        self._rect(LM, y, CW, ROW + 1 * mm, CYAN)
        self._text('TOTAL',  LM + sn + 2 * mm,        y - ROW + 2.5 * mm, 'Helvetica-Bold', 10, WHITE)
        self._text('20',     LM + sn + cat + mk / 2,   y - ROW + 2.5 * mm, 'Helvetica-Bold', 10, WHITE, 'C')
        ts = str(rec.total_score) if rec.total_score is not None else '—'
        self._text(ts, LM + sn + cat + mk + sc / 2, y - ROW + 2.5 * mm,
                   'Helvetica-Bold', 13, WHITE, 'C')
        y -= ROW + 3 * mm

        if has_ov and rec.score_override_by:
            self._text(
                f'* Scores modified by: {rec.score_override_by.get_full_name()}  ({_d(rec.score_override_at)})',
                LM, y, sz=7, col=LABEL)
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

    # ── Employee Information ─────────────────────────────────────────────────
    b.bar('EMPLOYEE INFORMATION')
    b.info_row('Name / Nom',        emp.user.get_full_name(),
               'Position / Poste',  emp.position or '—')
    b.info_row('Department',        str(emp.department or '—'),
               'Date Hired',        _d(emp.date_joined_company), shade=True)
    b.info_row('Period / Trimestre', rec.cycle.get_trimester_dates(),
               'Year / Année',       str(rec.cycle.year))
    b.y -= 2 * mm

    # ── Sections 1 & 2: Job identification & Tasks ───────────────────────────
    b.bar('1 & 2.  JOB IDENTIFICATION & TASKS')
    b.text_box('Summary of main job attributions / tasks:', rec.tasks_summary)
    b.text_box('Tasks assimilated by the employee:', rec.tasks_assimilated, max_lines=3)

    # Legend
    b.need(5 * mm)
    b._text(
        'Mastery levels:  1 = Does not meet   2 = Some difficulties   '
        '3 = Meets requirements   4 = Exceeds   5 = Greatly exceeds',
        LM, b.y - 1.5 * mm, sz=7, col=LABEL)
    b.y -= 5 * mm

    # ── Section 3: Appraisee self-rating ────────────────────────────────────
    b.bar('3.  APPRAISEE SELF-RATING  (Filled by Employee)')
    self_pf = {f: getattr(rec, f) for f, _ in PF_ROWS}
    self_aa = {f: getattr(rec, f) for f, _ in AA_ROWS}
    b.two_tables(PF_ROWS, self_pf, AA_ROWS, self_aa,
                 'Performance Factors', 'Attitude & Aptitude Factors')
    b.y -= 1 * mm

    # ── Section 4: Appraiser rating ──────────────────────────────────────────
    b.bar('4.  APPRAISER RATING  (Supervisor / Line Manager — Original Scores)')
    mgr_pf = {f: getattr(rec, f) for f, _ in MGR_PF}
    mgr_aa = {f: getattr(rec, f) for f, _ in MGR_AA}
    b.two_tables(MGR_PF, mgr_pf, MGR_AA, mgr_aa,
                 'Performance Factors', 'Attitude & Aptitude Factors')
    b.y -= 2 * mm

    # ── Section 4b: Score modifications — only shown when scores were changed ─
    b.override_diff_table()

    # ── Section 4c: Independent scores by reviewer level ─────────────────────
    b.ind_scores_table()

    # ── Section 5: Goals ─────────────────────────────────────────────────────
    b.bar('5.  GOALS TO REACH  (Agreed Action Points)')
    b.text_box('Goals:', rec.goals_to_reach, max_lines=4)

    # ── Section 6: Disciplinary sanctions ───────────────────────────────────
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
    b._rect(LM, b.y, CW, RH, CYAN)
    b._text('Sanction Type', LM + 2 * mm, b.y - RH + 2 * mm, 'Helvetica-Bold', 8, WHITE)
    b._text('YES', LM + col_yes + CW * 0.065, b.y - RH + 2 * mm, 'Helvetica-Bold', 8, WHITE, 'C')
    b._text('NO',  LM + col_no  + CW * 0.07,  b.y - RH + 2 * mm, 'Helvetica-Bold', 8, WHITE, 'C')
    b.y -= RH
    for idx, (key, label) in enumerate(sanctions):
        bg = LCYAN if idx % 2 else WHITE
        b._rect(LM, b.y, CW, RH, bg, BORD, 0.3)
        b._text(label, LM + 2 * mm, b.y - RH + 2 * mm, sz=8, col=DARK)
        cy = b.y - RH / 2 - 0.5 * mm
        if disc['counts'].get(key, 0):
            b._text('✓', LM + col_yes + CW * 0.065, cy, 'Helvetica-Bold', 11, CYAN, 'C')
        else:
            b._text('✓', LM + col_no  + CW * 0.07,  cy, 'Helvetica-Bold', 11, LABEL, 'C')
        b.y -= RH
    b._rect(LM, b.y, CW, RH, LCYAN, BORD, 0.4)
    b._text('Total Deduction:', LM + 2 * mm, b.y - RH + 2 * mm, 'Helvetica-Bold', 8, LABEL)
    b._text(str(disc['deduction']), LM + col_yes - 8 * mm, b.y - RH + 2 * mm,
            'Helvetica-Bold', 10, CYAN if disc['deduction'] < 0 else LABEL)
    b.y -= RH + 2 * mm

    # ── Section 7: Awards ────────────────────────────────────────────────────
    b.bar('7.  AWARDS RECEIVED')
    awards_list = [
        ('Employee of the Month', rec.award_employee_of_month),
        (f'Other: {rec.award_other or "—"}', bool(rec.award_other)),
    ]
    b.need((len(awards_list) + 1) * RH)
    b._rect(LM, b.y, CW, RH, CYAN)
    b._text('Award', LM + 2 * mm, b.y - RH + 2 * mm, 'Helvetica-Bold', 8, WHITE)
    b._text('YES',   LM + col_yes + CW * 0.065, b.y - RH + 2 * mm, 'Helvetica-Bold', 8, WHITE, 'C')
    b._text('NO',    LM + col_no  + CW * 0.07,  b.y - RH + 2 * mm, 'Helvetica-Bold', 8, WHITE, 'C')
    b.y -= RH
    for idx, (label, has_it) in enumerate(awards_list):
        bg = LCYAN if idx % 2 else WHITE
        b._rect(LM, b.y, CW, RH, bg, BORD, 0.3)
        b._text(label, LM + 2 * mm, b.y - RH + 2 * mm, sz=8, col=DARK)
        cy = b.y - RH / 2 - 0.5 * mm
        if has_it:
            b._text('✓', LM + col_yes + CW * 0.065, cy, 'Helvetica-Bold', 11, CYAN, 'C')
        else:
            b._text('✓', LM + col_no  + CW * 0.07,  cy, 'Helvetica-Bold', 11, LABEL, 'C')
        b.y -= RH
    b.y -= 2 * mm

    # ── Section 8: Employee comments & signature ─────────────────────────────
    b.bar('8.  EMPLOYEE COMMENTS & SIGNATURE')
    for label, val in [
        ('Comment on Self-Assessment', rec.comment_on_self),
        ('Comment on Supervision',     rec.comment_on_supervision),
        ('Comment on Organisation',    rec.comment_on_org),
    ]:
        b.text_box(label, val, max_lines=4)
    b.sig_strip(rec.employee, rec.employee_signed_at, rec.employee_sig_b64)

    # ── Co-worker ─────────────────────────────────────────────────────────────
    b.comment_block(
        'CO-WORKER / COLLÈGUE',
        rec.coworker_comment, rec.coworker_signed_by,
        rec.coworker_signed_at, rec.coworker_sig_b64)

    # ── Supervisor ───────────────────────────────────────────────────────────
    b.comment_block(
        'SUPERVISOR COMMENT & SIGNATURE  (Appraiser)',
        rec.unit_head_comment, rec.unit_head_signed_by,
        rec.unit_head_signed_at, rec.unit_head_sig_b64)

    # ── Upper hierarchy ───────────────────────────────────────────────────────
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

    # ── Total Ratings by Administration (LAST, after all signatures) ─────────
    b.bar('TOTAL RATINGS BY ADMINISTRATION')
    b.total_table(disc)

    # Closing note
    b.need(8 * mm)
    b._text(
        'Appraisal feedback to be provided to staff by end of first month of next Trimester.',
        LM, b.y - 2 * mm, sz=7.5, col=LABEL)

    b._end_page()
    b.cv.save()
    buf.seek(0)
    return buf
