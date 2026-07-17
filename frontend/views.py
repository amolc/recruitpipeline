from functools import wraps
import re
from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from api.models import Company, JobPosition


def candidate_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('candidate_login')
        if not request.user.roles.filter(role='candidate', is_active=True).exists():
            return redirect('candidate_login')
        return view_func(request, *args, **kwargs)
    return wrapper


def landing(request):
    companies = Company.objects.filter(is_active=True)
    return render(request, 'frontend/landing.html', {'companies': companies})


def register_company(request):
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        if not name:
            messages.error(request, 'Company name is required.')
            return redirect('landing')

        slug = re.sub(r'[^a-z0-9-]+', '-', name.lower()).strip('-')
        original_slug = slug
        counter = 1
        while Company.objects.filter(slug=slug).exists():
            slug = f'{original_slug}-{counter}'
            counter += 1

        company = Company.objects.create(
            name=name,
            slug=slug,
            address=request.POST.get('address', '').strip(),
            summary=request.POST.get('summary', '').strip(),
        )
        messages.success(request, f'"{name}" registered! You can now log in.')
        return redirect('landing')

    return redirect('landing')


def apply(request, company_slug=None):
    if not request.company:
        raise Http404('Company not found')
    positions = JobPosition.objects.filter(company=request.company, is_active=True)
    return render(request, 'frontend/apply.html', {
        'company': request.company,
        'positions': positions,
    })


def candidate_login(request, company_slug=None):
    if request.user.is_authenticated:
        if request.user.roles.filter(role='candidate', is_active=True).exists():
            return redirect('candidate_dashboard')
        logout(request)

    error = None
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        pin = request.POST.get('pin', '').strip()
        user = authenticate(request, phone=phone, pin=pin)
        if user and user.roles.filter(role='candidate', is_active=True).exists():
            login(request, user)
            request.session['role'] = 'candidate'
            return redirect('candidate_dashboard')
        if user:
            error = 'You do not have candidate access.'
        else:
            error = 'Invalid phone or PIN.'
    return render(request, 'frontend/portal/candidate_login.html', {'error': error})


@candidate_required
def candidate_dashboard(request, company_slug=None):
    return render(request, 'frontend/portal/candidate_dashboard.html')


def candidate_logout(request, company_slug=None):
    logout(request)
    return redirect('candidate_login')
