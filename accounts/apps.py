from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        from django.db.models.signals import post_save
        from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
        from django.dispatch import receiver

        @receiver(post_save, sender='accounts.Employee')
        def create_onboarding_checklist(sender, instance, created, **kwargs):
            if created:
                from .models import OnboardingChecklist
                OnboardingChecklist.objects.get_or_create(employee=instance)

        @receiver(user_logged_in)
        def on_login(sender, request, user, **kwargs):
            try:
                from dashboard.models import AuditLog
                from .audit_utils import log_action
                log_action(user, AuditLog.ACTION_LOGIN, 'User logged in', request=request)
            except Exception:
                pass

        @receiver(user_logged_out)
        def on_logout(sender, request, user, **kwargs):
            try:
                from dashboard.models import AuditLog
                from .audit_utils import log_action
                log_action(user, AuditLog.ACTION_LOGOUT, 'User logged out', request=request)
            except Exception:
                pass

        @receiver(user_login_failed)
        def on_login_failed(sender, credentials, request, **kwargs):
            try:
                from dashboard.models import AuditLog
                from .audit_utils import log_action
                username = credentials.get('username', '?')
                log_action(None, AuditLog.ACTION_LOGIN,
                           f'Failed login attempt for username: {username}',
                           request=request)
            except Exception:
                pass
