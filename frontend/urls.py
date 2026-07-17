from django.urls import path
from . import views

urlpatterns = [
    path('', views.landing, name='landing'),
    path('register/', views.register_company, name='register_company'),
    path('apply/', views.apply, name='apply'),
]
