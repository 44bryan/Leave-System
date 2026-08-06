from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect
from django.http import FileResponse, HttpResponse
from django.views.generic import TemplateView
import os


def serve_sw(request):
    """Serve service worker from root scope so it can control all pages."""
    sw_path = os.path.join(settings.BASE_DIR, 'static', 'sw.js')
    response = FileResponse(open(sw_path, 'rb'), content_type='application/javascript')
    response['Service-Worker-Allowed'] = '/'
    return response


urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('leaves/', include('leaves.urls')),
    path('dashboard/', include('dashboard.urls')),
    path('discipline/', include('discipline.urls')),
    path('contracts/', include('contracts.urls')),
    path('notifications/', include('notifications.urls')),
    path('appraisals/', include('appraisals.urls')),
    path('payroll/', include('payroll.urls')),
    path('recognition/', include('recognition.urls')),
    path('recruitment/', include('recruitment.urls')),
    path('medical-leave/', include('medical_leave.urls')),
    path('offboarding/', include('offboarding.urls')),
    # PWA
    path('sw.js', serve_sw, name='sw'),
    path('offline/', TemplateView.as_view(template_name='offline.html'), name='offline'),
    path('', lambda request: redirect('dashboard:home'), name='home'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
