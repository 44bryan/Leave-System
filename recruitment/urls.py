from django.urls import path
from . import views

app_name = 'recruitment'

urlpatterns = [
    # HR management (login required)
    path('',                                              views.posting_list,    name='list'),
    path('new/',                                          views.posting_create,  name='create'),
    path('<int:pk>/edit/',                                views.posting_edit,    name='edit'),
    path('<int:pk>/delete/',                              views.posting_delete,  name='delete'),
    path('<int:pk>/form-config/',                         views.form_config,     name='form_config'),
    path('<int:pk>/scoring/',                             views.scoring_config,  name='scoring_config'),
    path('<int:pk>/applicants/',                          views.applicant_list,  name='applicant_list'),
    path('<int:posting_pk>/applicants/<int:pk>/',         views.applicant_detail, name='applicant_detail'),
    path('<int:pk>/ai-analyse/',                          views.ai_analyse,       name='ai_analyse'),

    # Public job board (no login)
    path('jobs/',                views.job_board,     name='job_board'),
    path('jobs/<int:pk>/',       views.job_detail,    name='job_detail'),
    path('jobs/<int:pk>/apply/', views.apply,         name='apply'),
    path('jobs/<int:pk>/apply/success/', views.apply_success, name='apply_success'),
]
