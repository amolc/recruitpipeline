from django.urls import path
from . import views

app_name = 'recruitpanel'

urlpatterns = [
    path('login/', views.login_view, name='recruitpanel_login'),
    path('logout/', views.logout_view, name='recruitpanel_logout'),
    path('register/', views.register_company, name='register'),
    path('dashboard/', views.dashboard, name='recruitpanel_dashboard'),
    path('board/', views.board, name='board'),
    path('candidates/', views.candidate_list, name='candidate_list'),
    path('candidates/create/', views.candidate_create, name='candidate_create'),
    path('candidates/<int:pk>/', views.candidate_detail, name='candidate_detail'),
    path('candidates/<int:pk>/edit/', views.candidate_edit, name='candidate_edit'),
    path('candidates/<int:pk>/delete/', views.candidate_delete, name='candidate_delete'),
    path('positions/', views.job_positions, name='job_positions'),
    path('positions/add/', views.job_position_add, name='job_position_add'),
    path('positions/<int:pk>/', views.job_position_detail, name='job_position_detail'),
    path('positions/<int:pk>/edit/', views.job_position_edit, name='job_position_edit'),
    path('positions/<int:pk>/delete/', views.job_position_delete, name='job_position_delete'),
    path('positions/<int:position_pk>/automation/<str:stage>/', views.update_automation, name='update_automation'),
    path('panelist/', views.panelist, name='panelist'),
    path('screenings/', views.screenings, name='screenings'),
    path('pipeline/', views.pipeline, name='pipeline'),
    path('pipeline/add/', views.add_stage, name='add_stage'),
    path('pipeline/<str:stage_key>/delete/', views.delete_stage, name='delete_stage'),
    path('pipeline/<str:stage>/', views.update_global_automation, name='update_global_automation'),
    path('users/', views.user_list, name='user_list'),
    path('users/create/', views.user_create, name='user_create'),
    path('', views.dashboard, name='recruitpanel_home'),
]
