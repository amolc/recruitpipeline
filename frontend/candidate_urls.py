from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.candidate_login, name='candidate_login'),
    path('logout/', views.candidate_logout, name='candidate_logout'),
    path('register/', views.candidate_register, name='candidate_register'),
    path('dashboard/', views.candidate_dashboard, name='candidate_dashboard'),
    path('profile/', views.candidate_profile, name='candidate_profile'),
    path('profile/edit/', views.candidate_edit_profile, name='candidate_edit_profile'),
    path('jobs/', views.candidate_jobs, name='candidate_jobs'),
    path('applications/', views.candidate_applications, name='candidate_applications'),
    path('upload-resume/', views.upload_resume, name='upload_resume'),
    path('api/profile/', views.api_candidate_profile, name='api_candidate_profile'),
    path('api/skills/', views.api_skills, name='api_skills'),
    path('api/jobs/search/', views.api_jobs_search, name='api_jobs_search'),
    path('api/apply/', views.api_apply_job, name='api_apply_job'),
    path('', views.candidate_dashboard, name='candidate_home'),
]
