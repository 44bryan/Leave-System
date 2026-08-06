from django.contrib import admin
from django.urls import path, include
from django.conf.urls.i18n import i18n_patterns
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect


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
    path('', lambda request: redirect('dashboard:home'), name='home'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
