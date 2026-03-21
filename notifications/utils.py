import logging
import threading
from .models import Notification

logger = logging.getLogger(__name__)

_TYPE_COLOR = {
    'leave_submitted':        '#0A4D68',
    'leave_manager_approved': '#059669',
    'leave_hr_approved':      '#059669',
    'leave_approved':         '#059669',
    'leave_rejected':         '#dc2626',
    'leave_cancelled':        '#6b7a8d',
    'discipline':             '#d97706',
    'contract_issued':        '#0891b2',
    'contract_renewed':       '#7c3aed',
    'contract_terminated':    '#dc2626',
    'account_activated':      '#059669',
    'birthday':               '#f59e0b',
    'system':                 '#374151',
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
        if not getattr(settings, 'EMAIL_NOTIFICATIONS_ENABLED', False):
            logger.debug('EMAIL_NOTIFICATIONS_ENABLED is False — skipping email for "%s"', title)
            return
        if not user.email:
            logger.warning('Email skipped: user "%s" has no email address.', user.username)
            return

        from django.core.mail import EmailMultiAlternatives

        color      = _TYPE_COLOR.get(notification_type, '#374151')
        first_name = user.first_name or user.username

        site_base = getattr(settings, 'SITE_URL', '').rstrip('/')
        app_url   = (site_base + url) if (url and url.startswith('/')) else url

        # Logo hosted on Railway — Gmail won't display base64, needs a real URL
        logo_img = (
            f'<img src="{site_base}/static/LOGO.png" '
            f'alt="Magrabi ICO Cameroon Eye Institution" '
            f'width="160" style="max-width:160px;height:auto;display:block;margin:0 auto;" />'
        ) if site_base else (
            '<p style="margin:0;font-size:16px;font-weight:800;color:#0A4D68;'
            'letter-spacing:1px;">Magrabi ICO Cameroon</p>'
        )

        # Plain-text version
        plain = (
            f"Dear {first_name},\n\n"
            f"{title}\n\n"
            f"{message}\n\n"
            + (f"View in LeaveDesk: {app_url}\n\n" if app_url else "")
            + "—\nLeaveDesk HR | Magrabi ICO Cameroon Eye Institution\n"
              "This is an automated message. Please do not reply."
        )

        # CTA button
        btn = (
            f'<tr><td style="padding-top:28px;">'
            f'<a href="{app_url}" style="display:inline-block;'
            f'background-color:{color};color:#ffffff;text-decoration:none;'
            f'font-size:14px;font-weight:600;padding:12px 30px;'
            f'border-radius:6px;font-family:Arial,sans-serif;">'
            f'Open in LeaveDesk &rarr;</a></td></tr>'
        ) if app_url else ''

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
</head>
<body style="margin:0;padding:0;background:#f0f4f8;
             font-family:Arial,'Helvetica Neue',sans-serif;color:#1a202c;">

  <table width="100%" cellpadding="0" cellspacing="0"
         style="background:#f0f4f8;padding:40px 16px;">
    <tr><td align="center">
      <table width="580" cellpadding="0" cellspacing="0"
             style="max-width:580px;width:100%;">

        <!-- Logo header (white) -->
        <tr>
          <td style="background:#ffffff;border-radius:10px 10px 0 0;
                     padding:24px 40px;border-bottom:1px solid #e8edf2;
                     text-align:center;">
            {logo_img}
          </td>
        </tr>

        <!-- Card body -->
        <tr>
          <td style="background:#ffffff;border-radius:0 0 10px 10px;
                     border-top:3px solid {color};
                     box-shadow:0 4px 16px rgba(0,0,0,0.08);">
            <table width="100%" cellpadding="0" cellspacing="0">

              <!-- Title block -->
              <tr>
                <td style="padding:32px 40px 0 40px;">
                  <p style="margin:0 0 6px 0;font-size:11px;font-weight:700;
                             color:{color};letter-spacing:2px;
                             text-transform:uppercase;">
                    HR Notification
                  </p>
                  <h1 style="margin:0 0 20px 0;font-size:20px;font-weight:700;
                              color:#0d1b2a;line-height:1.35;">
                    {title}
                  </h1>
                  <p style="margin:0;font-size:15px;color:#374151;">
                    Dear <strong>{first_name}</strong>,
                  </p>
                </td>
              </tr>

              <!-- Message -->
              <tr>
                <td style="padding:16px 40px 0 40px;">
                  <div style="font-size:15px;color:#4a5568;line-height:1.8;
                               border-left:3px solid {color};padding-left:16px;">
                    {message.replace(chr(10), '<br>')}
                  </div>
                </td>
              </tr>

              <!-- Button -->
              <tr>
                <td style="padding:0 40px;">
                  <table cellpadding="0" cellspacing="0">{btn}</table>
                </td>
              </tr>

              <!-- Divider -->
              <tr>
                <td style="padding:32px 40px 0 40px;">
                  <div style="height:1px;background:#e2e8f0;"></div>
                </td>
              </tr>

              <!-- Footer -->
              <tr>
                <td style="padding:20px 40px 32px 40px;">
                  <p style="margin:0;font-size:12px;color:#a0aec0;line-height:1.7;">
                    This is an automated notification from
                    <strong style="color:#718096;">LeaveDesk HR</strong>
                    &mdash; Magrabi ICO Cameroon Eye Institution.<br>
                    Please do not reply. Log in to manage your notifications.
                  </p>
                </td>
              </tr>

            </table>
          </td>
        </tr>

        <!-- Bottom note -->
        <tr>
          <td style="padding-top:18px;text-align:center;">
            <p style="margin:0;font-size:11px;color:#a0aec0;">
              &copy; Magrabi ICO Cameroon Eye Institution &mdash; All rights reserved
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
            logger.info('Email sent to %s: "%s"', user.email, title)
        except Exception as smtp_err:
            logger.error('Failed to send email to %s ("%s"): %s', user.email, title, smtp_err)

    except Exception as e:
        logger.error('Unexpected error in _send_email for user %s: %s',
                     getattr(user, 'username', '?'), e)
