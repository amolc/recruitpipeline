from django.urls import path
from django.views.generic.base import RedirectView
from . import views

urlpatterns = [
    path('login/', views.login_view, name='admin_login'),
    path('logout/', views.logout_view, name='admin_logout'),
    path('board/', views.board, name='admin_board'),
    path('candidates/', views.candidate_list, name='candidate_list'),
    path('candidates/create/', views.candidate_create, name='candidate_create'),
    path('candidates/<int:pk>/', views.candidate_detail, name='candidate_detail'),
    path('candidates/<int:pk>/edit/', views.candidate_edit, name='candidate_edit'),
    path('candidates/<int:pk>/delete/', views.candidate_delete, name='candidate_delete'),
    path('job-positions/', views.job_positions, name='job_positions'),
    path('job-positions/add/', views.job_position_add, name='job_position_add'),
    path('job-positions/<int:pk>/', views.job_position_detail, name='job_position_detail'),
    path('job-positions/<int:pk>/edit/', views.job_position_edit, name='job_position_edit'),
    path('job-positions/<int:pk>/delete/', views.job_position_delete, name='job_position_delete'),
    path('job-positions/<int:position_pk>/automation/<str:stage>/', views.update_automation, name='update_automation'),
    path('panelist/', views.panelist, name='panelist'),
    path('screenings/', views.screenings, name='screenings'),
    path('pipeline/', views.pipeline, name='pipeline'),
    path('pipeline/add/', views.add_stage, name='add_stage'),
    path('pipeline/<str:stage_key>/delete/', views.delete_stage, name='delete_stage'),
    path('pipeline/<str:stage>/', views.update_global_automation, name='update_global_automation'),
    path('', RedirectView.as_view(pattern_name='candidate_list')),
]
