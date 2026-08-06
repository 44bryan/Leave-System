from django.urls import path
from . import views

app_name = 'offboarding'

urlpatterns = [
    path('', views.exit_list, name='exit_list'),
    path('new/', views.exit_create, name='exit_create'),
    path('<int:pk>/', views.exit_detail, name='exit_detail'),
]
