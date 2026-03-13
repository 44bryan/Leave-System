from django.urls import path
from . import views

app_name = 'contracts'

urlpatterns = [
    path('', views.contract_list, name='list'),
    path('issue/', views.issue_contract, name='issue'),
    path('my/', views.my_contract, name='my_contract'),
    path('notifications/', views.my_notifications, name='notifications'),
    path('<int:pk>/', views.contract_detail, name='detail'),
    path('<int:pk>/renew/', views.renew_contract, name='renew'),
    path('<int:pk>/terminate/', views.terminate_contract, name='terminate'),
    path('stats/', views.contract_stats, name='stats'),
]
