from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.http import HttpResponse


def csrf_debug_view(request, reason=""):
    origin = request.META.get('HTTP_ORIGIN', 'NOT PRESENT')
    referer = request.META.get('HTTP_REFERER', 'NOT PRESENT')
    host = request.META.get('HTTP_HOST', 'NOT PRESENT')
    trusted = getattr(settings, 'CSRF_TRUSTED_ORIGINS', [])
    return HttpResponse(
        f"CSRF FAILURE\nReason: {reason}\nOrigin: {origin}\nReferer: {referer}\nHost: {host}\nCSRF_TRUSTED_ORIGINS: {trusted}",
        content_type='text/plain',
        status=403,
    )


def debug_settings(request):
    trusted = getattr(settings, 'CSRF_TRUSTED_ORIGINS', 'NOT SET')
    failure_view = getattr(settings, 'CSRF_FAILURE_VIEW', 'NOT SET')
    debug = getattr(settings, 'DEBUG', 'NOT SET')
    return HttpResponse(
        f"VERSION: v2\nDEBUG: {debug}\nCSRF_TRUSTED_ORIGINS: {trusted}\nCSRF_FAILURE_VIEW: {failure_view}",
        content_type='text/plain',
    )


urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('leaves/', include('leaves.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('discipline/', include('discipline.urls')),
    path('contracts/', include('contracts.urls')),
    path('notifications/', include('notifications.urls')),
    path('', lambda request: redirect('dashboard:home'), name='home'),
    path('debug-settings/', debug_settings),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
