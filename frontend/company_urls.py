from django.urls import path
from . import views

urlpatterns = [
    path('', views.apply, name='company_apply'),
    path('apply/', views.apply, name='apply'),
]
