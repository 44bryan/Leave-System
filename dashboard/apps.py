from django.apps import AppConfig


class DashboardConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'dashboard'

    def ready(self):
        from django.contrib.auth.signals import user_logged_in, user_logged_out
        from django.dispatch import receiver
        from .models import AuditLog

        @receiver(user_logged_in)
        def on_login(sender, request, user, **kwargs):
            ip = (
                request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
                or request.META.get('REMOTE_ADDR')
            ) or None
            AuditLog.objects.create(
                user=user,
                action=AuditLog.ACTION_LOGIN,
                description=f"{user.get_full_name() or user.username} logged in",
                ip_address=ip,
            )

        @receiver(user_logged_out)
        def on_logout(sender, request, user, **kwargs):
            if not user:
                return
            ip = (
                request.META.get('HTTP_X_FORWARDED_FOR', '').split(',')[0].strip()
                or request.META.get('REMOTE_ADDR')
            ) or None
            AuditLog.objects.create(
                user=user,
                action=AuditLog.ACTION_LOGOUT,
                description=f"{user.get_full_name() or user.username} logged out",
                ip_address=ip,
            )
