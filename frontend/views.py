from functools import wraps
import re
from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from api.models import Company, JobPosition, UserAuth, UserRole

User = get_user_model()


def login_view(request):
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

        if not phone or not pin:
            error = 'Phone number and PIN are required.'
        else:
            user = authenticate(request, phone=phone, pin=pin)
            if user is None:
                if UserAuth.objects.filter(phone=phone).exists():
                    error = 'Invalid PIN.'
                else:
                    username = phone
                    base_username = username
                    counter = 1
                    while User.objects.filter(username=username).exists():
                        username = f'{base_username}-{counter}'
                        counter += 1

                    secretname = f'user{phone[-4:]}'
                    user = User.objects.create_user(username=username)
                    user_auth = UserAuth.objects.create(user=user, phone=phone, secretname=secretname)
                    user_auth.set_pin(pin)
                    user_auth.save()
                    user = authenticate(request, phone=phone, pin=pin)

            if user:
                login(request, user)
                active_roles = user.roles.filter(is_active=True)
                count = active_roles.count()

                if count == 1:
                    role = active_roles.first()
                    request.session['role'] = role.role
                    if role.company:
                        request.session['company_id'] = role.company.id
                    return redirect(role_redirect_url(role.role))
                else:
                    return redirect('choose_role')

    return render(request, 'frontend/login.html', {'error': error})


def role_redirect_url(role):
    from django.urls import reverse
    mapping = {
        'recruiter': 'recruitpanel:recruitpanel_dashboard',
        'candidate': 'candidate_dashboard',
        'superadmin': 'superadmin:superadmin_dashboard',
    }
    return reverse(mapping.get(role, 'landing'))


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

    companies = Company.objects.filter(is_active=True)
    return render(request, 'frontend/landing.html', {'companies': companies})


def choose_role(request):
    if not request.user.is_authenticated:
        return redirect('login')

    error = None
    if request.method == 'POST':
        selected = request.POST.get('role', '')
        if selected == 'candidate':
            if not request.user.roles.filter(role='candidate', is_active=True).exists():
                UserRole.objects.create(
                    user=request.user,
                    role='candidate',
                    is_active=True,
                )
            request.session['role'] = 'candidate'
            return redirect('candidate_dashboard')
        elif selected == 'recruiter':
            if request.user.roles.filter(role='recruiter', is_active=True).exists():
                request.session['role'] = 'recruiter'
                return redirect('recruitpanel:recruitpanel_dashboard')
            return redirect('register_company')
        else:
            error = 'Please select a role.'

    return render(request, 'frontend/choose_role.html', {'error': error})


def register_company(request):
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        name = request.POST.get('name', '').strip()

        if not phone or not name:
            messages.error(request, 'Phone number and company name are required.')
            return redirect('register_company')

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

        if request.user.is_authenticated:
            user = request.user
        else:
            if UserAuth.objects.filter(phone=phone).exists():
                messages.error(request, 'This phone number is already registered. Please sign in.')
                company.delete()
                return redirect('login')

            username = phone
            base_username = username
            c = 1
            while User.objects.filter(username=username).exists():
                username = f'{base_username}-{c}'
                c += 1

            pin = phone[-4:]
            secretname = re.sub(r'[^a-z0-9]', '', name.lower())[:20] or 'recruiter'

            user = User.objects.create_user(username=username)
            user_auth = UserAuth.objects.create(user=user, phone=phone, secretname=secretname)
            user_auth.set_pin(pin)
            user_auth.save()

            user = authenticate(request, phone=phone, pin=pin)

        if not user.roles.filter(role='recruiter', company=company).exists():
            UserRole.objects.create(
                user=user,
                role='recruiter',
                company=company,
                sub_role='admin',
                is_active=True,
            )

        if user and not request.user.is_authenticated:
            login(request, user)

        request.session['role'] = 'recruiter'
        request.session['company_id'] = company.id

        messages.success(request, f'Company "{name}" registered!')
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
