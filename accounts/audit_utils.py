"""
Audit logging utilities — thin wrapper around dashboard.models.AuditLog.
Call log_action() from any view to record who did what.
"""


def _get_ip(request):
    if request is None:
        return None
    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    return xff.split(',')[0].strip() if xff else request.META.get('REMOTE_ADDR')


def log_action(user, action, description, request=None, target_user=None):
    """
    Record an action in the audit log.

    Parameters
    ----------
    user         : User instance (or None for system/anonymous actions)
    action       : one of AuditLog.ACTION_* constants
    description  : human-readable description of the action
    request      : HttpRequest — used to capture IP address
    target_user  : the User that was acted on (optional)
    """
    try:
        from dashboard.models import AuditLog
        ip = _get_ip(request)
        AuditLog.objects.create(
            user=user,
            action=action,
            description=description,
            ip_address=ip,
            target_user=target_user,
        )
    except Exception:
        pass  # never let audit logging crash a real request
