from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
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
]
