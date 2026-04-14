"""
AEF HRM — Enterprise Hosting Budget Proposal PDF
Professional budget document to present to Africa Eye Foundation management.
"""
import os
from datetime import date
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.lib.utils import simpleSplit

W, H = A4
LM = 15 * mm
RM = W - 15 * mm
CW = RM - LM

CYAN  = (0.192, 0.722, 0.812)
BLUE  = (0.141, 0.588, 0.729)
DARK  = (0.024, 0.098, 0.118)
LABEL = (0.086, 0.325, 0.365)
BORD  = (0.700, 0.850, 0.900)
LCYAN = (0.906, 0.965, 0.980)
WHITE = (1.0,   1.0,   1.0)
GREEN = (0.06,  0.45,  0.06)

HEADER_H = 30 * mm
FOOTER_H =  8 * mm


# ── primitives ────────────────────────────────────────────────────────────────

def _rect(cv, x, y_top, w, h, fill, stroke=None, lw=0.4):
    cv.setFillColorRGB(*fill)
    if stroke:
        cv.setStrokeColorRGB(*stroke)
        cv.setLineWidth(lw)
        cv.rect(x, y_top - h, w, h, fill=1, stroke=1)
    else:
        cv.rect(x, y_top - h, w, h, fill=1, stroke=0)


def _text(cv, s, x, y, font='Helvetica', sz=9, col=DARK, align='L'):
    cv.setFillColorRGB(*col)
    cv.setFont(font, sz)
    s = str(s)
    if   align == 'C': cv.drawCentredString(x, y, s)
    elif align == 'R': cv.drawRightString(x, y, s)
    else:               cv.drawString(x, y, s)


def _wrap(cv, txt, x, y, max_w, sz=8.5, col=DARK, leading=4.5):
    for ln in simpleSplit(txt or '', 'Helvetica', sz, max_w):
        _text(cv, ln, x, y, sz=sz, col=col)
        y -= leading * mm
    return y


def _header(cv, pg):
    _rect(cv, 0, H, W, HEADER_H, WHITE)
    lp = os.path.join(os.path.dirname(__file__), 'static', 'LOGO.png')
    if os.path.exists(lp):
        cv.drawImage(lp, LM, H - HEADER_H + 6 * mm,
                     width=50 * mm, height=18 * mm,
                     preserveAspectRatio=True, mask='auto')
    cv.setFont('Helvetica-Bold', 14); cv.setFillColorRGB(*BLUE)
    cv.drawString(LM + 55 * mm, H - 11 * mm, 'ENTERPRISE SOFTWARE HOSTING BUDGET')
    cv.setFont('Helvetica', 9); cv.setFillColorRGB(*LABEL)
    cv.drawString(LM + 55 * mm, H - 17 * mm, 'AEF HRM System  —  Africa Eye Foundation')
    cv.setFont('Helvetica', 9); cv.setFillColorRGB(*LABEL)
    cv.drawString(LM + 55 * mm, H - 23 * mm, f'Prepared: {date.today().strftime("%d %B %Y")}')
    cv.setFont('Helvetica', 7.5); cv.setFillColorRGB(*LABEL)
    cv.drawRightString(RM, H - 10 * mm, f'Page {pg}')
    cv.setStrokeColorRGB(*CYAN); cv.setLineWidth(2.2)
    cv.line(0, H - HEADER_H, W, H - HEADER_H)


def _footer(cv):
    cv.setStrokeColorRGB(*CYAN); cv.setLineWidth(0.8)
    cv.line(0, FOOTER_H, W, FOOTER_H)
    cv.setFont('Helvetica', 6.5); cv.setFillColorRGB(*LABEL)
    cv.drawString(LM, FOOTER_H - 4 * mm, 'Africa Eye Foundation  ·  AEF HRM System  ·  CONFIDENTIAL')
    cv.drawRightString(RM, FOOTER_H - 4 * mm, f'Generated {date.today().strftime("%d/%m/%Y")}')


def _bar(cv, y, label):
    h = 7 * mm
    _rect(cv, LM, y, CW, h, CYAN)
    _text(cv, label, LM + 3 * mm, y - h + 2.5 * mm, 'Helvetica-Bold', 9, WHITE)
    return y - h - 2 * mm


class Page:
    def __init__(self, path):
        self.cv  = canvas.Canvas(path, pagesize=A4)
        self.pg  = 1
        self.y   = 0
        self._new()

    def _new(self):
        _header(self.cv, self.pg)
        self.y = H - HEADER_H - 5 * mm

    def need(self, h):
        if self.y - h < FOOTER_H + 8 * mm:
            _footer(self.cv)
            self.cv.showPage()
            self.pg += 1
            self._new()

    def bar(self, label):
        self.need(10 * mm)
        self.y = _bar(self.cv, self.y, label)

    def save(self):
        _footer(self.cv)
        self.cv.save()


# ── column widths for main cost table ─────────────────────────────────────────
# No. | Component | Provider | Monthly (USD) | Monthly (XAF) | Annual (XAF)
cN  = LM;             wN  =  8 * mm
cC  = cN  + wN;       wC  = 45 * mm
cPR = cC  + wC;       wPR = 28 * mm
cMU = cPR + wPR;      wMU = 22 * mm
cMX = cMU + wMU;      wMX = 26 * mm
cAX = cMX + wMX;      wAX = CW - wN - wC - wPR - wMU - wMX


def _tbl_header(p):
    h = 7 * mm
    _rect(p.cv, LM, p.y, CW, h, BLUE)
    for lbl, x, w in [
        ('#',              cN,  wN),
        ('Component',      cC,  wC),
        ('Provider',       cPR, wPR),
        ('Monthly (USD)',  cMU, wMU),
        ('Monthly (XAF)', cMX, wMX),
        ('Annual (XAF)',   cAX, wAX),
    ]:
        align = 'R' if lbl in ('Monthly (USD)', 'Monthly (XAF)', 'Annual (XAF)') else 'L'
        xd = (x + w - 2 * mm) if align == 'R' else (x + 2 * mm)
        _text(p.cv, lbl, xd, p.y - h + 2.5 * mm, 'Helvetica-Bold', 8, WHITE, align)
    p.y -= h


def _tbl_row(p, no, comp, prov, usd_mo, xaf_mo, xaf_yr, shade=False, bold=False, total=False):
    h  = 9 * mm
    bg = CYAN if total else (LCYAN if shade else WHITE)
    _rect(p.cv, LM, p.y, CW, h, bg, BORD, 0.3)
    fn  = 'Helvetica-Bold' if (bold or total) else 'Helvetica'
    tc  = WHITE if total else (BLUE if bold else DARK)
    lc  = WHITE if total else LABEL
    _text(p.cv, no,     cN  + 2 * mm,    p.y - h + 3 * mm, fn, 8.5,  tc)
    _text(p.cv, comp,   cC  + 2 * mm,    p.y - h + 3 * mm, fn, 8.5,  tc)
    _text(p.cv, prov,   cPR + 2 * mm,    p.y - h + 3 * mm, 'Helvetica', 7.5, lc)
    _text(p.cv, usd_mo, cMU + wMU - 2*mm, p.y - h + 3 * mm, fn, 9,   tc, 'R')
    _text(p.cv, xaf_mo, cMX + wMX - 2*mm, p.y - h + 3 * mm, fn, 9,   tc, 'R')
    _text(p.cv, xaf_yr, cAX + wAX - 2*mm, p.y - h + 3 * mm, fn, 10,  WHITE if total else BLUE, 'R')
    p.y -= h


def build():
    out = os.path.join(os.path.dirname(__file__), 'AEF_HRM_Enterprise_Budget.pdf')
    p   = Page(out)

    # ── INTRODUCTION ─────────────────────────────────────────────────────────
    intro_lines = [
        'This budget document outlines all recurring costs required to host and operate the',
        'AEF HRM System as a fully functional enterprise application for Africa Eye Foundation.',
        'Costs cover application hosting, managed database, professional email delivery, and',
        'domain name registration. All USD figures are converted at 1 USD = 600 XAF.',
    ]
    for ln in intro_lines:
        _text(p.cv, ln, LM, p.y - 2 * mm, sz=9, col=DARK)
        p.y -= 5 * mm
    p.y -= 3 * mm

    # ── SECTION 1: DETAILED COST TABLE ───────────────────────────────────────
    p.bar('1.  ITEMISED ANNUAL BUDGET')

    _tbl_header(p)

    rows = [
        # No, Component, Provider, USD/mo, XAF/mo, XAF/yr, shade, bold, total
        ('1', 'Application Hosting',
         'Railway — Hobby Plan',
         '$5.00', '3,000', '36,000', False, False, False),

        ('2', 'Managed Database (PostgreSQL)',
         'Railway — Database Add-on',
         '$5.00', '3,000', '36,000', True, False, False),

        ('3', 'Professional Email Delivery',
         'Resend — Pro Plan',
         '$20.00', '12,000', '144,000', False, False, False),

        ('4', 'Domain Name (.com)',
         'Namecheap / GoDaddy',
         '$1.17', '700', '8,400', True, False, False),

        ('5', 'SSL / HTTPS Certificate',
         'Let\'s Encrypt (auto via Railway)',
         'FREE', 'FREE', 'FREE', False, False, False),

        ('6', 'Static Files & Media Serving',
         'WhiteNoise (built into app)',
         'FREE', 'FREE', 'FREE', True, False, False),

        ('', 'TOTAL ANNUAL COST',
         '',
         '$31.17', '18,700', '224,400', False, True, True),
    ]

    for no, comp, prov, usd, xaf_m, xaf_y, shade, bold, total in rows:
        p.need(10 * mm)
        _tbl_row(p, no, comp, prov, usd, xaf_m, xaf_y, shade, bold, total)

    p.y -= 5 * mm

    # ── SECTION 2: COMPONENT DESCRIPTIONS ────────────────────────────────────
    p.bar('2.  WHAT EACH COMPONENT DOES')

    components = [
        (
            '1. Application Hosting — Railway Hobby Plan  ($5/month)',
            'Railway is the cloud platform that runs the AEF HRM web application 24 hours a day, '
            '7 days a week. It keeps the system accessible to all staff at all times, handles '
            'incoming requests (login, leave applications, appraisals, PDF downloads), and '
            'automatically redeploys the latest version each time the developer pushes an update. '
            'The Hobby plan ensures the application never sleeps or goes offline during working hours.'
        ),
        (
            '2. Managed Database — Railway PostgreSQL  ($5/month)',
            'The database stores all system data: employee records, leave requests and balances, '
            'appraisal results and scores, discipline records, contracts, notifications, and user '
            'accounts. Railway manages backups, security, and uptime automatically. Without the '
            'database the system cannot function. The add-on provides 1 GB of storage which is '
            'more than sufficient for an organisation of 50–200 staff.'
        ),
        (
            '3. Professional Email Delivery — Resend Pro  ($20/month)',
            'The system sends automated emails for every key event: new employee onboarding '
            '(welcome email with login credentials), leave request approvals and rejections, '
            'appraisal stage notifications (when it is your turn to fill), contract alerts, '
            'and password resets. Resend Pro supports up to 50,000 emails per month and '
            'guarantees delivery through verified sending domains, preventing emails from '
            'landing in spam. A professional email service is essential for staff to trust '
            'and use the system reliably.'
        ),
        (
            '4. Domain Name  (~$1.17/month — billed annually at ~$14/year)',
            'A domain name gives the system a professional and memorable web address such as '
            'hrm.aef-cameroon.org or aef-hrm.com instead of a technical URL. Staff access '
            'the system by typing the domain in their browser. The domain is registered once '
            'per year through a domain registrar (Namecheap or GoDaddy). First-year promotions '
            'often reduce the cost to under $2; standard renewal is $10–$15/year.'
        ),
        (
            '5. SSL / HTTPS Certificate  (FREE)',
            'SSL encrypts all data transmitted between staff browsers and the server, ensuring '
            'that passwords, appraisal scores, and personal records cannot be intercepted. '
            'Railway issues and renews SSL certificates automatically at no charge through '
            'Let\'s Encrypt. The padlock icon in the browser confirms the connection is secure.'
        ),
        (
            '6. Static Files & Media Serving  (FREE)',
            'CSS stylesheets, JavaScript, icons, and the company logo are served directly by '
            'the application using WhiteNoise, a library already integrated into the system. '
            'This eliminates the need for a separate CDN or file storage subscription, '
            'keeping the total cost as low as possible.'
        ),
    ]

    for title, desc in components:
        lines = simpleSplit(desc, 'Helvetica', 8.5, CW - 6 * mm)
        block_h = 7 * mm + len(lines) * 4.8 * mm + 5 * mm
        p.need(block_h)

        # title strip
        _rect(p.cv, LM, p.y, CW, 7 * mm, LCYAN, BORD, 0.4)
        _text(p.cv, title, LM + 3 * mm, p.y - 5 * mm, 'Helvetica-Bold', 8.5, BLUE)
        p.y -= 7 * mm

        # body
        bh = len(lines) * 4.8 * mm + 4 * mm
        _rect(p.cv, LM, p.y, CW, bh, WHITE, BORD, 0.4)
        cy = p.y - 3.5 * mm
        for ln in lines:
            _text(p.cv, ln, LM + 3 * mm, cy, sz=8.5, col=DARK)
            cy -= 4.8 * mm
        p.y -= bh + 2 * mm

    # ── SECTION 3: PAYMENT SCHEDULE ──────────────────────────────────────────
    p.bar('3.  PAYMENT SCHEDULE')

    sched = [
        ('Monthly Recurring',
         'Railway (Hosting + Database)',
         'Card / Bank Transfer',
         '$10.00 / month',
         '6,000 XAF / month'),
        ('Monthly Recurring',
         'Resend (Email Delivery)',
         'Card / Bank Transfer',
         '$20.00 / month',
         '12,000 XAF / month'),
        ('Annual (once/year)',
         'Domain Name Renewal',
         'Card / Bank Transfer',
         '~$14.00 / year',
         '~8,400 XAF / year'),
    ]

    sh = 8 * mm
    cols_s = [
        ('Frequency',  LM,              40 * mm),
        ('Item',       LM + 40 * mm,    45 * mm),
        ('Payment',    LM + 85 * mm,    30 * mm),
        ('USD',        LM + 115 * mm,   25 * mm),
        ('XAF',        LM + 140 * mm,   CW - 140 * mm),
    ]
    p.need(sh + len(sched) * sh + 3 * mm)
    _rect(p.cv, LM, p.y, CW, sh, BLUE)
    for lbl, x, w in cols_s:
        _text(p.cv, lbl, x + 2 * mm, p.y - sh + 2.5 * mm, 'Helvetica-Bold', 8, WHITE)
    p.y -= sh

    for idx, (freq, item, pay, usd, xaf) in enumerate(sched):
        bg = LCYAN if idx % 2 else WHITE
        _rect(p.cv, LM, p.y, CW, sh, bg, BORD, 0.3)
        _text(p.cv, freq, LM + 2 * mm,              p.y - sh + 2.5 * mm, sz=8.5, col=DARK)
        _text(p.cv, item, LM + 40 * mm + 2 * mm,    p.y - sh + 2.5 * mm, sz=8.5, col=DARK)
        _text(p.cv, pay,  LM + 85 * mm + 2 * mm,    p.y - sh + 2.5 * mm, sz=8,   col=LABEL)
        _text(p.cv, usd,  LM + 115 * mm + 2 * mm,   p.y - sh + 2.5 * mm, 'Helvetica-Bold', 8.5, BLUE)
        _text(p.cv, xaf,  LM + 140 * mm + 2 * mm,   p.y - sh + 2.5 * mm, 'Helvetica-Bold', 8.5, LABEL)
        p.y -= sh

    p.y -= 5 * mm

    # ── SECTION 4: SUMMARY BOX ───────────────────────────────────────────────
    p.bar('4.  BUDGET SUMMARY')
    p.y -= 2 * mm

    summary = [
        ('Total Monthly Cost (USD)',  '$31.17 / month'),
        ('Total Monthly Cost (XAF)',  '18,700 XAF / month'),
        ('Total Annual Cost (USD)',   '$374.04 / year'),
        ('Total Annual Cost (XAF)',   '224,400 XAF / year'),
    ]

    sh2 = 9 * mm
    hw  = CW / 2
    for idx, (lbl, val) in enumerate(summary):
        bg = LCYAN if idx % 2 else WHITE
        p.need(sh2)
        _rect(p.cv, LM,      p.y, hw, sh2, bg, BORD, 0.4)
        _rect(p.cv, LM + hw, p.y, hw, sh2, bg, BORD, 0.4)
        _text(p.cv, lbl, LM + 2 * mm,      p.y - sh2 + 3 * mm, sz=8.5, col=LABEL)
        _text(p.cv, val, LM + hw + 2 * mm, p.y - sh2 + 3 * mm, 'Helvetica-Bold', 10, BLUE)
        p.y -= sh2

    p.y -= 4 * mm

    # Grand total highlight
    p.need(12 * mm)
    _rect(p.cv, LM, p.y, CW, 12 * mm, CYAN)
    _text(p.cv, 'TOTAL ANNUAL INVESTMENT:',
          LM + 4 * mm, p.y - 4 * mm, 'Helvetica-Bold', 11, WHITE)
    _text(p.cv, '224,400 XAF / year    ($374.04)',
          LM + 4 * mm, p.y - 9 * mm, 'Helvetica-Bold', 13, WHITE)
    p.y -= 14 * mm

    p.y -= 5 * mm

    # ── NOTE ─────────────────────────────────────────────────────────────────
    p.need(28 * mm)
    note = (
        'Note: All prices above are based on current provider rates as at April 2026. '
        'Railway and Resend pricing may be subject to change — the figures above should '
        'be treated as indicative. The system is already configured and integrated with '
        'Railway (hosting), Railway PostgreSQL (database), and Resend (email). No '
        'additional developer setup costs are required to activate these services. '
        'Payment is made directly to each provider by the organisation via credit/debit '
        'card or bank transfer.'
    )
    note_lines = simpleSplit(note, 'Helvetica', 8.5, CW - 6 * mm)
    nh = len(note_lines) * 4.8 * mm + 6 * mm
    _rect(p.cv, LM, p.y, CW, nh, LCYAN, CYAN, 1.2)
    cy = p.y - 4 * mm
    for ln in note_lines:
        _text(p.cv, ln, LM + 3 * mm, cy, sz=8.5, col=DARK)
        cy -= 4.8 * mm
    p.y -= nh + 5 * mm

    # Signatures / approval section
    p.need(30 * mm)
    _rect(p.cv, LM, p.y, CW, 7 * mm, BLUE)
    _text(p.cv, 'APPROVED BY', LM + 3 * mm, p.y - 5 * mm, 'Helvetica-Bold', 9, WHITE)
    p.y -= 7 * mm

    sig_cols = [
        ('Prepared by (Developer)', LM,            CW / 3 - 2 * mm),
        ('Reviewed by (HR)',         LM + CW / 3,  CW / 3 - 2 * mm),
        ('Approved by (Management)', LM + 2*CW/3,  CW / 3),
    ]
    sig_h = 22 * mm
    _rect(p.cv, LM, p.y, CW, sig_h, WHITE, BORD, 0.4)
    for lbl, x, w in sig_cols:
        _text(p.cv, lbl,           x + 2 * mm, p.y - 4  * mm, sz=7, col=LABEL)
        _text(p.cv, 'Name: ____________________', x + 2 * mm, p.y - 10 * mm, sz=8, col=DARK)
        _text(p.cv, 'Sign: ____________________', x + 2 * mm, p.y - 16 * mm, sz=8, col=DARK)
        _text(p.cv, 'Date: ____________________', x + 2 * mm, p.y - 21 * mm, sz=8, col=DARK)
    p.y -= sig_h

    p.save()
    print(f'Saved: {out}')
    return out


if __name__ == '__main__':
    build()
