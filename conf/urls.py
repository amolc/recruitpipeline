from django.contrib import admin
from django.urls import include, path
from django.conf import settings
from django.conf.urls.static import static
from adminpanel import views as admin_views
from frontend import views as frontend_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('superadmin/', include('superadmin.urls')),
    path('register/', frontend_views.register_company, name='register_company'),
    path('adminpanel/', admin_views.super_dashboard, name='super_dashboard'),
    path('adminpanel/companies/', admin_views.super_companies, name='super_companies'),
    path('adminpanel/companies/create/', admin_views.super_company_create, name='super_company_create'),
    path('adminpanel/companies/<int:pk>/', admin_views.super_company_detail, name='super_company_detail'),
    path('adminpanel/companies/<int:pk>/edit/', admin_views.super_company_edit, name='super_company_edit'),
    path('adminpanel/candidates/', admin_views.super_candidates, name='super_candidates'),
    path('adminpanel/positions/', admin_views.super_positions, name='super_positions'),
    path('adminpanel/users/', admin_views.super_users, name='super_users'),
    path('adminpanel/users/create/', admin_views.super_user_create, name='super_user_create'),
    path('candidate/', include('frontend.candidate_urls')),
    path('recruitpanel/', include('recruitpanel.urls')),
    path('<slug:company_slug>/', include('adminpanel.urls')),
    path('<slug:company_slug>/', include('frontend.company_urls')),
    path('<slug:company_slug>/api/', include('api.urls')),
    path('<slug:company_slug>/api/', include('agents.urls')),
    path('', include('frontend.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
