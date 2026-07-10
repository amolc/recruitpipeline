from django.urls import path
from . import views

urlpatterns = [
    path('apply/', views.submit_application, name='submit_application'),
    path('apply/<int:application_id>/status/', views.update_status, name='update_status'),
    path('positions/', views.list_positions, name='list_positions'),
]
