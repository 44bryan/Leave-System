from django.urls import path
from . import views

app_name = 'appraisals'

urlpatterns = [
    # Employee
    path('my/',                          views.my_appraisals,     name='my_appraisals'),
    path('fill/<int:record_pk>/',        views.employee_fill,     name='employee_fill'),
    path('detail/<int:record_pk>/',      views.appraisal_detail,  name='detail'),

    # Signing chain
    path('coworker/<int:record_pk>/',    views.coworker_fill,     name='coworker_fill'),
    path('unit-head/<int:record_pk>/',   views.unit_head_fill,    name='unit_head_fill'),
    path('manager/<int:record_pk>/',     views.manager_fill,      name='manager_fill'),
    path('hr-review/<int:record_pk>/',   views.hr_fill,           name='hr_fill'),
    path('director/<int:record_pk>/',    views.director_fill,     name='director_fill'),
    path('ceo/<int:record_pk>/',         views.ceo_fill,          name='ceo_fill'),

    # Pending queues
    path('pending/coworker/',            views.pending_coworker,  name='pending_coworker'),
    path('pending/unit-head/',           views.pending_unit_head, name='pending_unit_head'),
    path('pending/manager/',             views.pending_manager,   name='pending_manager'),
    path('pending/hr/',                  views.pending_hr,        name='pending_hr'),
    path('pending/director/',            views.pending_director,  name='pending_director'),
    path('pending/ceo/',                 views.pending_ceo,       name='pending_ceo'),

    # PDF download
    path('pdf/<int:record_pk>/',         views.appraisal_pdf,     name='pdf'),

    # HR management
    path('hr/',                               views.hr_dashboard,       name='hr_dashboard'),
    path('hr/initiate/',                      views.hr_initiate,        name='hr_initiate'),
    path('hr/deadline-missed/',               views.hr_deadline_missed,  name='hr_deadline_missed'),
    path('hr/unlock/<int:record_pk>/',        views.hr_unlock_employee,  name='hr_unlock_employee'),
    path('cycles/<int:cycle_pk>/',            views.cycle_records,       name='cycle_records'),
    path('cycles/<int:cycle_pk>/distribute/', views.distribute,          name='distribute'),
]
