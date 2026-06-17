def system_settings_ctx(request):
    try:
        from .models import SystemSettings
        return {'system_settings': SystemSettings.get()}
    except Exception:
        return {'system_settings': None}
