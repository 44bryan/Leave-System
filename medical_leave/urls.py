from django.urls import path
from . import views

app_name = 'medical_leave'

urlpatterns = [
    # Physician
    path('issue/', views.issue, name='issue'),
    path('my-issued/', views.physician_list, name='physician_list'),

    # Employee self-view
    path('my/', views.my_sick_leaves, name='my_sick_leaves'),

    # Detail & print
    path('<int:pk>/view/', views.detail, name='detail'),
    path('<int:pk>/print/', views.print_view, name='print'),

    # Line Manager
    path('lm-queue/', views.lm_queue, name='lm_queue'),
    path('<int:pk>/endorse/line-manager/', views.lm_endorse, name='lm_endorse'),

    # HR
    path('hr-queue/', views.hr_queue, name='hr_queue'),
    path('<int:pk>/endorse/hr/', views.hr_endorse, name='hr_endorse'),

    # All records
    path('all/', views.all_records, name='all_records'),
]
