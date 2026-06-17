from .models import SystemSettings


def system_settings_ctx(request):
    return {'system_settings': SystemSettings.get()}
