from django.urls import path, re_path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('apply/', views.apply, name='apply'),
    re_path(r'^serve-media/(?P<file_path>.+)$', views.serve_resume_file, name='serve_resume_file'),
]
