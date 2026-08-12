from django.urls import path
from . import views

app_name = 'training'

urlpatterns = [
    path('', views.trainee_list, name='trainee_list'),
    path('add/', views.trainee_add, name='trainee_add'),
    path('<int:pk>/edit/', views.trainee_edit, name='trainee_edit'),
    path('<int:pk>/delete/', views.trainee_delete, name='trainee_delete'),
    path('export/excel/', views.export_excel, name='export_excel'),
    path('export/pdf/', views.export_pdf, name='export_pdf'),
]
