from functools import wraps
import re
from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from api.models import Company, JobPosition, UserAuth, UserRole

User = get_user_model()


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
    if request.user.is_authenticated:
        roles = request.user.roles.filter(is_active=True)
        if roles.filter(role='recruiter').exists():
            return redirect('recruitpanel:recruitpanel_dashboard')
        if roles.filter(role='candidate').exists():
            return redirect('candidate_dashboard')
        if roles.filter(role='superadmin').exists():
            return redirect('superadmin:superadmin_dashboard')
        logout(request)

    error = None
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        pin = request.POST.get('pin', '').strip()
        portal = request.POST.get('portal', '')
        user = authenticate(request, phone=phone, pin=pin)
        if user:
            if portal == 'recruiter' and user.roles.filter(role='recruiter', is_active=True).exists():
                login(request, user)
                request.session['role'] = 'recruiter'
                role = user.roles.filter(role='recruiter', is_active=True).first()
                if role.company:
                    request.session['company_id'] = role.company.id
                return redirect('recruitpanel:recruitpanel_dashboard')
            elif portal == 'candidate' and user.roles.filter(role='candidate', is_active=True).exists():
                login(request, user)
                request.session['role'] = 'candidate'
                return redirect('candidate_dashboard')
            elif portal == 'superadmin' and user.roles.filter(role='superadmin', is_active=True).exists():
                login(request, user)
                request.session['role'] = 'superadmin'
                return redirect('superadmin:superadmin_dashboard')
            else:
                error = f'You do not have {portal} access.'
        else:
            error = 'Invalid phone or PIN.'

    return render(request, 'frontend/landing.html', {'error': error})


def register_company(request):
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        name = request.POST.get('name', '').strip()

        if not phone or not name:
            messages.error(request, 'Phone number and company name are required.')
            return redirect('landing')

        if UserAuth.objects.filter(phone=phone).exists():
            messages.error(request, 'This phone number is already registered.')
            return redirect('landing')

        slug = re.sub(r'[^a-z0-9-]+', '-', name.lower()).strip('-')
        if not slug:
            slug = 'company'
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

        username = phone
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f'{base_username}-{counter}'
            counter += 1

        pin = phone[-4:]
        secretname = re.sub(r'[^a-z0-9]', '', name.lower())[:20] or 'recruiter'

        user = User.objects.create_user(username=username)
        user_auth = UserAuth.objects.create(user=user, phone=phone, secretname=secretname)
        user_auth.set_pin(pin)
        user_auth.save()

        UserRole.objects.create(
            user=user,
            role='recruiter',
            company=company,
            sub_role='admin',
            is_active=True,
        )

        user = authenticate(request, phone=phone, pin=pin)
        if user:
            login(request, user)
            request.session['role'] = 'recruiter'
            request.session['company_id'] = company.id

        messages.success(
            request,
            f'Company "{name}" registered! Your login PIN is <strong>{pin}</strong>.',
        )
        return redirect('recruitpanel:recruitpanel_dashboard')

    return render(request, 'frontend/register.html')


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
    return redirect('landing')
