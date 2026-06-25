from django.urls import path
from . import views

app_name = 'recognition'

urlpatterns = [
    path('', views.proposal_list, name='list'),
    path('my-awards/', views.my_awards, name='my_awards'),
    path('propose/', views.propose, name='propose'),
    path('<int:pk>/', views.proposal_detail, name='detail'),
]
