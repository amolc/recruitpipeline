from django.urls import path
from . import views

app_name = 'superadmin'

urlpatterns = [
    path('login/', views.login_view, name='superadmin_login'),
    path('logout/', views.logout_view, name='superadmin_logout'),
    path('dashboard/', views.dashboard, name='superadmin_dashboard'),
    path('', views.dashboard, name='superadmin_home'),
]
