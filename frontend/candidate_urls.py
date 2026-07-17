from django.urls import path
from . import views

urlpatterns = [
    path('login/', views.candidate_login, name='candidate_login'),
    path('logout/', views.candidate_logout, name='candidate_logout'),
    path('dashboard/', views.candidate_dashboard, name='candidate_dashboard'),
    path('', views.candidate_dashboard, name='candidate_home'),
]
