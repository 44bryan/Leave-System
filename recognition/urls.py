from django.urls import path
from . import views

app_name = 'recognition'

urlpatterns = [
    path('', views.proposal_list, name='list'),
    path('propose/', views.propose, name='propose'),
    path('<int:pk>/', views.proposal_detail, name='detail'),
]
