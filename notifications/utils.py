from .models import Notification


def notify(recipient_user, title, message, notification_type='system', url=''):
    """Create an in-app notification and optionally send an email."""
    Notification.objects.create(
        recipient=recipient_user,
        title=title,
        message=message,
        notification_type=notification_type,
        url=url,
    )
    _send_email(recipient_user, title, message)


def _send_email(user, title, message):
    """Send email if EMAIL_NOTIFICATIONS_ENABLED=True and user has an email address."""
    try:
        from django.conf import settings
        if not getattr(settings, 'EMAIL_NOTIFICATIONS_ENABLED', False):
            return
        if not user.email:
            return
        from django.core.mail import send_mail
        send_mail(
            subject=f'[LeaveDesk] {title}',
            message=(
                f'{message}\n\n'
                f'---\n'
                f'This is an automated notification from LeaveDesk HR System.\n'
                f'Please do not reply to this email.'
            ),
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@leavedesk.com'),
            recipient_list=[user.email],
            fail_silently=True,
        )
    except Exception:
        pass
