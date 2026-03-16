from datetime import date

def notifications_ctx(request):
    """Inject unread notification count, recent notifications, and suspension status into every template."""
    if not request.user.is_authenticated:
        return {}
    try:
        qs = request.user.system_notifications
        unread = qs.filter(is_read=False).count()
        recent = list(qs.all()[:6])

        # Check if current employee is suspended
        is_suspended = False
        suspension_end = None
        try:
            emp = request.user.employee
            from discipline.models import DisciplineRecord
            today = date.today()
            active_suspension = DisciplineRecord.objects.filter(
                employee=emp,
                action_type='suspension',
                suspension_start__lte=today,
                suspension_end__gte=today,
            ).order_by('-suspension_end').first()
            if active_suspension:
                is_suspended = True
                suspension_end = active_suspension.suspension_end
        except Exception:
            pass

        return {
            'notif_unread': unread,
            'notif_recent': recent,
            'is_suspended': is_suspended,
            'suspension_end': suspension_end,
        }
    except Exception:
        return {'notif_unread': 0, 'notif_recent': [], 'is_suspended': False, 'suspension_end': None}
