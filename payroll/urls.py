from django.urls import path
from . import views

app_name = 'payroll'

urlpatterns = [
    path('', views.payslip_list, name='list'),
    path('create/', views.payslip_create, name='create'),
    path('<int:pk>/', views.payslip_detail, name='detail'),
    path('<int:pk>/delete/', views.payslip_delete, name='delete'),
    path('my/', views.my_payslips, name='my_payslips'),
    path('bulk-upload/', views.bulk_upload_payslips, name='bulk_upload'),
]
