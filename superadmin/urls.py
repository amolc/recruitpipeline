from django.urls import path
from . import views

app_name = 'superadmin'

urlpatterns = [
    path('login/', views.login_view, name='superadmin_login'),
    path('logout/', views.logout_view, name='superadmin_logout'),
    path('dashboard/', views.dashboard, name='superadmin_dashboard'),
    path('companies/', views.company_list, name='superadmin_companies'),
    path('companies/create/', views.company_create, name='superadmin_company_create'),
    path('companies/<int:pk>/', views.company_detail, name='superadmin_company_detail'),
    path('companies/<int:pk>/edit/', views.company_edit, name='superadmin_company_edit'),
    path('candidates/', views.candidates_list, name='superadmin_candidates'),
    path('positions/', views.positions_list, name='superadmin_positions'),
    path('users/', views.users_list, name='superadmin_users'),
    path('', views.dashboard, name='superadmin_home'),
]
