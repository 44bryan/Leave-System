from django.urls import path
from . import views

app_name = 'discipline'

urlpatterns = [
    path('', views.discipline_list, name='list'),
    path('issue/', views.issue_discipline, name='issue'),
    path('direct-issue/', views.direct_issue_discipline, name='direct_issue'),
    path('my-notices/', views.my_discipline_notices, name='my_notices'),
    path('<int:pk>/', views.discipline_detail, name='detail'),
    path('<int:pk>/propose/', views.propose_sanction, name='propose_sanction'),
    path('<int:pk>/execute/', views.execute_proposal, name='execute_proposal'),
    path('<int:pk>/delete/', views.delete_discipline_record, name='delete'),
    path('<int:pk>/upload/', views.discipline_upload_doc, name='upload_doc'),
    path('doc/<int:doc_pk>/delete/', views.discipline_delete_doc, name='delete_doc'),
    path('stats/', views.discipline_stats, name='stats'),
]
