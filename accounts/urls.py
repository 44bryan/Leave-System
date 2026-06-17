from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Password reset via email (self-service)
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='accounts/password_reset_form.html',
             email_template_name='accounts/password_reset_email.html',
             subject_template_name='accounts/password_reset_subject.txt',
             success_url='/accounts/password-reset/done/',
         ),
         name='password_reset'),
    path('password-reset/done/',
         auth_views.PasswordResetDoneView.as_view(
             template_name='accounts/password_reset_done.html',
         ),
         name='password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(
             template_name='accounts/password_reset_confirm.html',
             success_url='/accounts/password-reset/complete/',
         ),
         name='password_reset_confirm'),
    path('password-reset/complete/',
         auth_views.PasswordResetCompleteView.as_view(
             template_name='accounts/password_reset_complete.html',
         ),
         name='password_reset_complete'),

    path('profile/', views.profile_view, name='profile'),
    path('employees/', views.employee_list, name='employee_list'),
    path('employees/add/', views.employee_create, name='employee_create'),
    path('employees/<int:pk>/edit/', views.employee_edit, name='employee_edit'),
    path('employees/<int:pk>/delete/', views.employee_delete, name='employee_delete'),
    path('departments/', views.department_list, name='department_list'),
    path('departments/<int:pk>/delete/', views.department_delete, name='department_delete'),
    path('profile/change-password/', views.change_password, name='change_password'),
    path('profile/save-signature/', views.profile_save_signature, name='profile_save_signature'),
    path('employees/<int:pk>/reset-credentials/', views.admin_reset_credentials, name='reset_credentials'),
    path('employees/<int:pk>/set-signature/', views.set_employee_signature, name='set_employee_signature'),
    path('username-suggest/', views.username_suggest, name='username_suggest'),
    path('employees/import/', views.employee_import, name='employee_import'),
    path('employees/excel-upload/', views.employee_excel_upload, name='employee_excel_upload'),
    path('employees/bulk-assign/', views.bulk_assign_manager, name='bulk_assign_manager'),
    path('employees/export-credentials/', views.export_credentials, name='export_credentials'),
    path('employees/<int:pk>/history/', views.employee_history, name='employee_history'),
    path('employees/<int:employee_pk>/documents/upload/', views.document_upload, name='document_upload'),
    path('documents/<int:doc_pk>/delete/', views.document_delete, name='document_delete'),
    path('my-documents/', views.my_documents, name='my_documents'),
    path('my-documents/<int:doc_pk>/delete/', views.my_document_delete, name='my_document_delete'),
    path('onboarding/', views.onboarding_list, name='onboarding_list'),
    path('onboarding/<int:pk>/update/', views.onboarding_update, name='onboarding_update'),
    path('2fa/setup/', views.setup_2fa, name='setup_2fa'),
    path('2fa/verify/', views.verify_2fa, name='verify_2fa'),
    path('documents/expiring/', views.expiring_documents, name='expiring_documents'),
]
