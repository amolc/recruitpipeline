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
    path('applications/<int:application_id>/', views.candidate_application_detail, name='candidate_application_detail'),
    path('upload-resume/', views.upload_resume, name='upload_resume'),
    path('api/profile/', views.api_candidate_profile, name='api_candidate_profile'),
    path('api/upload-photo/', views.upload_photo, name='upload_photo'),
    path('api/skills/', views.api_skills, name='api_skills'),
    path('api/jobs/search/', views.api_jobs_search, name='api_jobs_search'),
    path('api/apply/', views.api_apply_job, name='api_apply_job'),
    path('api/generate-cover-letter/', views.api_generate_cover_letter, name='api_generate_cover_letter'),
    path('', views.candidate_dashboard, name='candidate_home'),
]
