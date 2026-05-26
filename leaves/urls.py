from django.urls import path
from . import views

app_name = 'leaves'

urlpatterns = [
    path('submit/', views.submit_leave, name='submit'),
    path('edit/<int:pk>/', views.leave_edit, name='edit'),
    path('my-requests/', views.my_requests, name='my_requests'),
    path('cancel/<int:pk>/', views.cancel_request, name='cancel'),
    path('detail/<int:pk>/', views.leave_detail, name='detail'),
    path('unit-head/pending/', views.unit_head_approvals, name='unit_head_approvals'),
    path('unit-head/action/<int:pk>/', views.unit_head_action, name='unit_head_action'),
    path('manager/pending/', views.manager_approvals, name='manager_approvals'),
    path('manager/action/<int:pk>/', views.manager_action, name='manager_action'),
    path('hr/pending/', views.hr_approvals, name='hr_approvals'),
    path('hr/action/<int:pk>/', views.hr_action, name='hr_action'),
    path('hr/all/', views.all_leaves_hr, name='all_leaves'),
    path('director/pending/', views.director_approvals, name='director_approvals'),
    path('director/action/<int:pk>/', views.director_action, name='director_action'),
    path('print/<int:pk>/', views.print_leave, name='print_leave'),
    path('pdf/<int:pk>/', views.pdf_leave, name='pdf_leave'),
    path('employee/<int:pk>/summary/', views.employee_leave_summary, name='employee_summary'),
    path('admin-override/<int:pk>/', views.admin_override_leave, name='admin_override'),
    path('admin-edit/<int:pk>/', views.admin_edit_leave, name='admin_edit'),
    path('leave-types/', views.leave_type_list, name='leave_type_list'),
    path('leave-types/add/', views.leave_type_create, name='leave_type_create'),
    path('leave-types/<int:pk>/edit/', views.leave_type_edit, name='leave_type_edit'),
    path('leave-types/<int:pk>/delete/', views.leave_type_delete, name='leave_type_delete'),
    path('leave-types/restore-defaults/', views.restore_default_leave_types, name='restore_default_leave_types'),
    path('hr/backfill-signatures/', views.backfill_signatures, name='backfill_signatures'),
    path('set-entitlement/', views.set_leave_entitlement, name='set_entitlement'),
]
