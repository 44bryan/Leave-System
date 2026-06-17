from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'accounts'

    def ready(self):
        from django.db.models.signals import post_save
        from django.dispatch import receiver

        @receiver(post_save, sender='accounts.Employee')
        def create_onboarding_checklist(sender, instance, created, **kwargs):
            if created:
                from .models import OnboardingChecklist
                OnboardingChecklist.objects.get_or_create(employee=instance)
