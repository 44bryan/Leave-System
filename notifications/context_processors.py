def notifications_ctx(request):
    """Inject unread notification count and recent notifications into every template."""
    if not request.user.is_authenticated:
        return {}
    try:
        qs = request.user.system_notifications
        unread = qs.filter(is_read=False).count()
        recent = list(qs.all()[:6])
        return {'notif_unread': unread, 'notif_recent': recent}
    except Exception:
        return {'notif_unread': 0, 'notif_recent': []}
