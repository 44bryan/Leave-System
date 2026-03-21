import logging
import threading
from .models import Notification
from .logo_b64 import LOGO_B64

logger = logging.getLogger(__name__)

# Label + accent color per notification type
_TYPE_STYLE = {
    'leave_submitted':        ('LEAVE REQUEST',  '#0A4D68'),
    'leave_manager_approved': ('APPROVED',        '#059669'),
    'leave_hr_approved':      ('APPROVED',        '#059669'),
    'leave_approved':         ('APPROVED',        '#059669'),
    'leave_rejected':         ('REJECTED',        '#dc2626'),
    'leave_cancelled':        ('CANCELLED',       '#6b7a8d'),
    'discipline':             ('DISCIPLINE',      '#d97706'),
    'contract_issued':        ('CONTRACT',        '#0891b2'),
    'contract_renewed':       ('CONTRACT RENEWAL','#7c3aed'),
    'contract_terminated':    ('CONTRACT ENDED',  '#dc2626'),
    'account_activated':      ('ACCOUNT',         '#059669'),
    'birthday':               ('BIRTHDAY',        '#f59e0b'),
    'system':                 ('NOTICE',          '#374151'),
}


def notify(recipient_user, title, message, notification_type='system', url=''):
    """Create an in-app notification and send an email in a background thread."""
    Notification.objects.create(
        recipient=recipient_user,
        title=title,
        message=message,
        notification_type=notification_type,
        url=url,
    )
    t = threading.Thread(
        target=_send_email,
        args=(recipient_user, title, message, notification_type, url),
        daemon=True,
    )
    t.start()


def _send_email(user, title, message, notification_type='system', url=''):
    """Send a professional HTML email if EMAIL_NOTIFICATIONS_ENABLED=True."""
    try:
        from django.conf import settings
        enabled = getattr(settings, 'EMAIL_NOTIFICATIONS_ENABLED', False)
        if not enabled:
            logger.debug('EMAIL_NOTIFICATIONS_ENABLED is False — skipping email for "%s"', title)
            return
        if not user.email:
            logger.warning(
                'Email notification skipped: user "%s" (pk=%s) has no email address.',
                user.username, user.pk
            )
            return
        from django.core.mail import EmailMultiAlternatives

        label, color = _TYPE_STYLE.get(notification_type, ('NOTICE', '#374151'))
        first_name = user.first_name or user.username

        site_base = getattr(settings, 'SITE_URL', '').rstrip('/')
        app_url = ''
        if url:
            app_url = (site_base + url) if url.startswith('/') else url

        # ── Plain-text fallback ───────────────────────────────────────────
        plain = (
            f"Dear {first_name},\n\n"
            f"{title}\n\n"
            f"{message}\n\n"
            + (f"View in LeaveDesk: {app_url}\n\n" if app_url else "")
            + "---\nMagrabi ICO Cameroon Eye Institution\n"
              "LeaveDesk HR System — automated notification. Please do not reply."
        )

        # ── CTA button ────────────────────────────────────────────────────
        btn_html = (
            f'<table cellpadding="0" cellspacing="0" style="margin-top:24px;">'
            f'<tr><td style="background:{color};border-radius:8px;">'
            f'<a href="{app_url}" '
            f'style="display:inline-block;padding:12px 28px;color:#ffffff;'
            f'text-decoration:none;font-weight:700;font-size:14px;'
            f'font-family:Arial,sans-serif;letter-spacing:.3px;">'
            f'Open in LeaveDesk &#8594;</a>'
            f'</td></tr></table>'
        ) if app_url else ''

        # ── HTML email ────────────────────────────────────────────────────
        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>{title}</title>
</head>
<body style="margin:0;padding:0;background-color:#eef2f6;
             font-family:Arial,'Helvetica Neue',Helvetica,sans-serif;">

  <table role="presentation" width="100%" cellpadding="0" cellspacing="0"
         style="background-color:#eef2f6;padding:40px 16px;">
    <tr><td align="center">

      <!-- Card -->
      <table role="presentation" width="600" cellpadding="0" cellspacing="0"
             style="max-width:600px;width:100%;background:#ffffff;
                    border-radius:12px;overflow:hidden;
                    box-shadow:0 4px 20px rgba(0,0,0,0.10);">

        <!-- ── TOP ACCENT BAR ── -->
        <tr>
          <td style="background:{color};height:5px;font-size:1px;line-height:1px;">&nbsp;</td>
        </tr>

        <!-- ── HEADER ── -->
        <tr>
          <td style="background:linear-gradient(135deg,#0A4D68 0%,#0e6b8a 100%);
                     padding:32px 40px;text-align:center;">

            <!-- Logo -->
            <img src="data:image/png;base64,{LOGO_B64}"
                 alt="Magrabi ICO Cameroon Eye Institution"
                 width="180"
                 style="max-width:180px;height:auto;display:block;
                        margin:0 auto 16px auto;" />

            <!-- Divider -->
            <div style="width:48px;height:2px;background:rgba(255,255,255,0.4);
                        margin:0 auto 14px auto;"></div>

            <!-- Badge -->
            <span style="display:inline-block;background:{color};
                         color:#ffffff;font-size:11px;font-weight:700;
                         letter-spacing:2px;padding:5px 16px;
                         border-radius:20px;text-transform:uppercase;">
              {label}
            </span>
          </td>
        </tr>

        <!-- ── GREETING ── -->
        <tr>
          <td style="padding:32px 40px 0 40px;">
            <p style="margin:0;font-size:16px;color:#1a2b3c;font-weight:600;">
              Dear {first_name},
            </p>
          </td>
        </tr>

        <!-- ── TITLE ── -->
        <tr>
          <td style="padding:16px 40px 0 40px;">
            <h1 style="margin:0;font-size:22px;font-weight:800;color:#0A4D68;
                       line-height:1.3;border-left:4px solid {color};
                       padding-left:14px;">
              {title}
            </h1>
          </td>
        </tr>

        <!-- ── MESSAGE ── -->
        <tr>
          <td style="padding:20px 40px 0 40px;">
            <div style="background:#f7fafc;border-radius:8px;padding:20px 22px;
                        font-size:15px;color:#374151;line-height:1.75;
                        border:1px solid #e5edf4;">
              {message.replace(chr(10), '<br>')}
            </div>
          </td>
        </tr>

        <!-- ── BUTTON ── -->
        <tr>
          <td style="padding:24px 40px 0 40px;">
            {btn_html}
          </td>
        </tr>

        <!-- ── DIVIDER ── -->
        <tr>
          <td style="padding:32px 40px 0 40px;">
            <div style="height:1px;background:#e5edf4;"></div>
          </td>
        </tr>

        <!-- ── FOOTER ── -->
        <tr>
          <td style="padding:24px 40px 32px 40px;text-align:center;">
            <p style="margin:0 0 6px 0;font-size:13px;font-weight:700;
                      color:#0A4D68;letter-spacing:.3px;">
              Magrabi ICO Cameroon Eye Institution
            </p>
            <p style="margin:0;font-size:12px;color:#9ab4c0;line-height:1.6;">
              This is an automated notification from <strong>LeaveDesk HR</strong>.<br>
              Please do not reply to this email.
              Log in to the system to manage your notifications.
            </p>
          </td>
        </tr>

        <!-- ── BOTTOM ACCENT BAR ── -->
        <tr>
          <td style="background:{color};height:4px;font-size:1px;line-height:1px;">&nbsp;</td>
        </tr>

      </table>
      <!-- /Card -->

      <!-- Outer footer note -->
      <p style="margin:20px 0 0 0;font-size:11px;color:#aab4c0;text-align:center;">
        &copy; Magrabi ICO Cameroon Eye Institution &mdash; LeaveDesk HR System
      </p>

    </td></tr>
  </table>

</body>
</html>"""

        email = EmailMultiAlternatives(
            subject=f'[LeaveDesk] {title}',
            body=plain,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'LeaveDesk HR <noreply@leavedesk.com>'),
            to=[user.email],
        )
        email.attach_alternative(html, 'text/html')
        try:
            email.send()
            logger.info('Email notification sent to %s: "%s"', user.email, title)
        except Exception as smtp_err:
            logger.error(
                'Failed to send email to %s (subject: "%s"): %s',
                user.email, title, smtp_err
            )

    except Exception as e:
        logger.error(
            'Unexpected error in _send_email for user %s: %s',
            getattr(user, 'username', '?'), e
        )
