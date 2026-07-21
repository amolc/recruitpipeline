import re
from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db.models import Count, Q
from company.models import Company
from api.models import Application, JobPosition, UserProfile, Stage, UserRole, UserAuth
from django.contrib.auth import get_user_model

User = get_user_model()


SUPERADMIN_LOGIN = 'superadmin:superadmin_login'
SUPERADMIN_DASHBOARD = 'superadmin:superadmin_dashboard'
SUPERADMIN_COMPANIES = 'superadmin:superadmin_companies'


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


@superadmin_required
def company_list(request):
    companies = Company.objects.annotate(
        candidate_count=Count('applications'),
        position_count=Count('job_positions'),
        user_count=Count('members'),
    ).order_by('-created_at')
    return render(request, 'superadmin/companies.html', {'companies': companies})


@superadmin_required
def company_detail(request, pk):
    company = get_object_or_404(Company, pk=pk)
    candidates = Application.objects.filter(company=company).order_by('-submitted_at')[:20]
    positions = JobPosition.objects.filter(company=company)
    members = UserProfile.objects.filter(company=company).select_related('user')
    stats = {
        'candidates': Application.objects.filter(company=company).count(),
        'positions': JobPosition.objects.filter(company=company).count(),
        'stages': Stage.objects.filter(company=company).count(),
        'members': members.count(),
    }
    return render(request, 'superadmin/company_detail.html', {
        'company': company,
        'candidates': candidates,
        'positions': positions,
        'members': members,
        'stats': stats,
    })


@superadmin_required
def company_edit(request, pk):
    company = get_object_or_404(Company, pk=pk)
    if request.method == 'POST':
        company.name = request.POST.get('name', company.name).strip()
        new_slug = re.sub(r'[^a-z0-9-]+', '-', company.name.lower()).strip('-')
        if new_slug != company.slug and Company.objects.filter(slug=new_slug).exists():
            original = new_slug
            counter = 1
            while Company.objects.filter(slug=new_slug).exists():
                new_slug = f'{original}-{counter}'
                counter += 1
        company.slug = new_slug
        company.brand_color = request.POST.get('brand_color', company.brand_color).strip()
        company.email = request.POST.get('email', '').strip()
        company.website = request.POST.get('website', '').strip()
        company.logo_url = request.POST.get('logo_url', '').strip()
        if request.FILES.get('logo'):
            company.logo = request.FILES['logo']
        company.address = request.POST.get('address', '').strip()
        company.summary = request.POST.get('summary', '').strip()
        company.is_active = request.POST.get('is_active') == 'on'
        company.save()
        messages.success(request, f'Company "{company.name}" updated.')
        return redirect(SUPERADMIN_COMPANIES)
    return render(request, 'superadmin/company_form.html', {'company': company})


@superadmin_required
def company_create(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        slug = re.sub(r'[^a-z0-9-]+', '-', name.lower()).strip('-')
        color = request.POST.get('brand_color', '#f59e0b').strip()
        if name:
            original_slug = slug
            counter = 1
            while Company.objects.filter(slug=slug).exists():
                slug = f'{original_slug}-{counter}'
                counter += 1
            company = Company.objects.create(
                name=name,
                slug=slug,
                brand_color=color,
                email=request.POST.get('email', '').strip(),
                website=request.POST.get('website', '').strip(),
                address=request.POST.get('address', '').strip(),
                summary=request.POST.get('summary', '').strip(),
            )
            if request.FILES.get('logo'):
                company.logo = request.FILES['logo']
                company.save()
            messages.success(request, f'Company "{name}" created.')
            return redirect(SUPERADMIN_COMPANIES)
        else:
            messages.error(request, 'Company name is required.')
    return render(request, 'superadmin/company_form.html', {'company': None})


@superadmin_required
def candidates_list(request):
    q = request.GET.get('q', '').strip()
    company_filter = request.GET.get('company', '')
    candidates = Application.objects.select_related('company')
    if q:
        candidates = candidates.filter(
            Q(full_name__icontains=q) |
            Q(email__icontains=q) |
            Q(phone__icontains=q)
        )
    if company_filter:
        candidates = candidates.filter(company__id=company_filter)
    candidates = candidates.order_by('-submitted_at')[:200]
    companies = Company.objects.order_by('name')
    return render(request, 'superadmin/candidates.html', {
        'candidates': candidates,
        'companies': companies,
        'q': q,
        'company_filter': company_filter,
    })


@superadmin_required
def positions_list(request):
    q = request.GET.get('q', '').strip()
    company_filter = request.GET.get('company', '')
    positions = JobPosition.objects.select_related('company')
    if q:
        positions = positions.filter(title__icontains=q)
    if company_filter:
        positions = positions.filter(company__id=company_filter)
    positions = positions.order_by('-created_at')[:200]
    companies = Company.objects.order_by('name')
    return render(request, 'superadmin/positions.html', {
        'positions': positions,
        'companies': companies,
        'q': q,
        'company_filter': company_filter,
    })


@superadmin_required
def users_list(request):
    q = request.GET.get('q', '').strip()
    users = User.objects.select_related('profile', 'auth').prefetch_related('roles')
    if q:
        users = users.filter(
            Q(username__icontains=q) |
            Q(email__icontains=q) |
            Q(auth__phone__icontains=q)
        )
    users = users.order_by('-date_joined')[:200]
    return render(request, 'superadmin/users.html', {
        'users': users,
        'q': q,
    })


def logout_view(request):
    logout(request)
    return redirect('landing')
