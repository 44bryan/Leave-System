import logging
import threading
from .models import Notification

logger = logging.getLogger(__name__)


# Icon + color per notification type (for HTML email)
_TYPE_STYLE = {
    'leave_submitted':        ('📋', '#0A4D68'),
    'leave_manager_approved': ('✅', '#059669'),
    'leave_hr_approved':      ('✅', '#059669'),
    'leave_approved':         ('✅', '#059669'),
    'leave_rejected':         ('❌', '#dc2626'),
    'leave_cancelled':        ('↩️',  '#6b7a8d'),
    'discipline':             ('⚠️',  '#d97706'),
    'contract_issued':        ('📄', '#0891b2'),
    'contract_renewed':       ('🔄', '#7c3aed'),
    'contract_terminated':    ('🚫', '#dc2626'),
    'account_activated':      ('👤', '#059669'),
    'birthday':               ('🎂', '#f59e0b'),
    'system':                 ('🔔', '#374151'),
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
    """Send an HTML email if EMAIL_NOTIFICATIONS_ENABLED=True and user has an email."""
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

        icon, color = _TYPE_STYLE.get(notification_type, ('🔔', '#374151'))
        first_name  = user.first_name or user.username

        # Build full URL if relative path given
        app_url = ''
        if url:
            base = getattr(settings, 'SITE_URL', '').rstrip('/')
            app_url = (base + url) if url.startswith('/') else url

        # ── Plain-text fallback ────────────────────────────────────────────
        plain = (
            f"Hello {first_name},\n\n"
            f"{title}\n\n"
            f"{message}\n\n"
            + (f"View in app: {app_url}\n\n" if app_url else "")
            + "---\nLeaveDesk HR System\nThis is an automated notification. Please do not reply."
        )

        # ── HTML email ─────────────────────────────────────────────────────
        btn_html = (
            f'<a href="{app_url}" '
            f'style="display:inline-block;margin-top:18px;padding:10px 24px;'
            f'background:{color};color:#ffffff;text-decoration:none;'
            f'border-radius:8px;font-weight:700;font-size:14px;">'
            f'View in LeaveDesk &rarr;</a>'
        ) if app_url else ''

        html = f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#f4f7fa;font-family:'Segoe UI',Arial,sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f7fa;padding:32px 0;">
    <tr><td align="center">
      <table width="600" cellpadding="0" cellspacing="0"
             style="background:#ffffff;border-radius:14px;overflow:hidden;
                    box-shadow:0 2px 12px rgba(0,0,0,0.08);max-width:600px;width:100%;">

        <!-- Header -->
        <tr>
          <td style="background:linear-gradient(135deg,#0A4D68,#088395);
                     padding:28px 32px;text-align:center;">
            <div style="font-size:28px;margin-bottom:6px;">{icon}</div>
            <div style="color:#ffffff;font-size:22px;font-weight:800;letter-spacing:-.5px;">
              LeaveDesk HR
            </div>
            <div style="color:rgba(255,255,255,.75);font-size:13px;margin-top:2px;">
              Eye Hospital — HR Notification System
            </div>
          </td>
        </tr>

        <!-- Body -->
        <tr>
          <td style="padding:32px;">
            <p style="margin:0 0 8px;font-size:13px;color:#9ab4c0;
                      text-transform:uppercase;letter-spacing:.07em;font-weight:700;">
              Notification
            </p>
            <h2 style="margin:0 0 16px;font-size:20px;color:#0d1b2a;font-weight:800;
                        border-left:4px solid {color};padding-left:12px;">
              {title}
            </h2>
            <p style="margin:0;font-size:15px;color:#374151;line-height:1.7;
                      background:#f8fafc;border-radius:8px;padding:16px;">
              {message.replace(chr(10), '<br>')}
            </p>
            {btn_html}
          </td>
        </tr>

        <!-- Footer -->
        <tr>
          <td style="background:#f8fafc;border-top:1px solid #e8f0f5;
                     padding:16px 32px;text-align:center;">
            <p style="margin:0;font-size:12px;color:#9ab4c0;line-height:1.6;">
              This is an automated notification from <strong>LeaveDesk HR System</strong>.<br>
              Please do not reply to this email. Log in to manage your notifications.
            </p>
          </td>
        </tr>

      </table>
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
