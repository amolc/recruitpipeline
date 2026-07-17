from functools import wraps
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.db.models import Count
from api.models import Company, Application, JobPosition, UserRole, UserAuth
from django.contrib.auth import get_user_model

User = get_user_model()


SUPERADMIN_LOGIN = 'superadmin:superadmin_login'
SUPERADMIN_DASHBOARD = 'superadmin:superadmin_dashboard'


def superadmin_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(SUPERADMIN_LOGIN)
        if not request.user.roles.filter(role='superadmin', is_active=True).exists():
            return redirect(SUPERADMIN_LOGIN)
        return view_func(request, *args, **kwargs)
    return wrapper


def login_view(request):
    if request.user.is_authenticated:
        if request.user.roles.filter(role='superadmin', is_active=True).exists():
            return redirect(SUPERADMIN_DASHBOARD)
        logout(request)

    error = None
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        pin = request.POST.get('pin', '').strip()
        user = authenticate(request, phone=phone, pin=pin)
        if user and user.roles.filter(role='superadmin', is_active=True).exists():
            login(request, user)
            request.session['role'] = 'superadmin'
            return redirect(SUPERADMIN_DASHBOARD)
        if user:
            error = 'You do not have superadmin access.'
        else:
            error = 'Invalid phone or PIN.'
    return render(request, 'superadmin/login.html', {'error': error})


@superadmin_required
def dashboard(request):
    stats = {
        'companies': Company.objects.count(),
        'candidates': Application.objects.count(),
        'positions': JobPosition.objects.count(),
        'users': User.objects.count(),
    }
    return render(request, 'superadmin/dashboard.html', {'stats': stats})


def logout_view(request):
    logout(request)
    return redirect('landing')
