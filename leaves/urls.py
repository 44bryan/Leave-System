from django.urls import path
from . import views

app_name = 'leaves'

urlpatterns = [
    path('submit/', views.submit_leave, name='submit'),
    path('my-requests/', views.my_requests, name='my_requests'),
    path('cancel/<int:pk>/', views.cancel_request, name='cancel'),
    path('detail/<int:pk>/', views.leave_detail, name='detail'),
    path('manager/pending/', views.manager_approvals, name='manager_approvals'),
    path('manager/action/<int:pk>/', views.manager_action, name='manager_action'),
    path('hr/pending/', views.hr_approvals, name='hr_approvals'),
    path('hr/action/<int:pk>/', views.hr_action, name='hr_action'),
    path('hr/all/', views.all_leaves_hr, name='all_leaves'),
]
