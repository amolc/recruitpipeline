from functools import wraps
from datetime import timedelta
from django.utils.timezone import now
import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.db import models
from django.http import JsonResponse, Http404
from django.db.models import Count
from company.models import Company, CompanyEditRequest
from api.models import Application, JobPosition, Automation, DEFAULT_AUTOMATIONS, Stage, UserRole, UserAuth, Screening, Panelist

User = get_user_model()

RECRUIT_LOGIN = 'recruitpanel:recruitpanel_login'
RECRUIT_DASHBOARD = 'recruitpanel:recruitpanel_dashboard'
RECRUIT_CANDIDATES = 'recruitpanel:candidate_list'
RECRUIT_POSITIONS = 'recruitpanel:job_positions'
RECRUIT_BOARD = 'recruitpanel:board'


def recruiter_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(RECRUIT_LOGIN)
        if not request.user.roles.filter(role='recruiter', is_active=True).exists():
            return redirect(RECRUIT_LOGIN)
        if not request.company:
            messages.error(request, 'No company selected.')
            return redirect(RECRUIT_LOGIN)
        return view_func(request, *args, **kwargs)
    return wrapper


def recruiter_active(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(RECRUIT_LOGIN)
        if not request.user.roles.filter(role='recruiter', is_active=True).exists():
            return redirect(RECRUIT_LOGIN)
        return view_func(request, *args, **kwargs)
    return wrapper


def login_view(request):
    if request.user.is_authenticated:
        if request.user.roles.filter(role='recruiter', is_active=True).exists():
            return redirect(RECRUIT_DASHBOARD)
        logout(request)

    error = None
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        pin = request.POST.get('pin', '').strip()
        user = authenticate(request, phone=phone, pin=pin)
        if user:
            roles = list(user.roles.filter(role='recruiter', is_active=True).select_related('company'))
            if roles:
                login(request, user)
                request.session['role'] = 'recruiter'
                if len(roles) == 1:
                    request.session['company_id'] = roles[0].company.id
                return redirect(RECRUIT_DASHBOARD)
            error = 'You do not have recruiter access.'
        else:
            error = 'Invalid phone or PIN.'

    return render(request, 'recruitpanel/login.html', {
        'error': error,
    })


@recruiter_active
def dashboard(request):
    company = request.company
    user_companies = Company.objects.filter(
        user_roles__user=request.user,
        user_roles__role='recruiter',
        user_roles__is_active=True,
    ).distinct()

    if company:
        stats = {
            'candidates': Application.objects.filter(company=company).count(),
            'positions': JobPosition.objects.filter(company=company).count(),
            'active_positions': JobPosition.objects.filter(company=company, is_active=True).count(),
        }
    else:
        stats = None

    return render(request, 'recruitpanel/dashboard.html', {
        'stats': stats,
        'company': company,
        'user_companies': user_companies,
    })


def logout_view(request):
    logout(request)
    return redirect('landing')


# ── Company Switching & Creation ──


@recruiter_active
def switch_company(request, company_id):
    company = get_object_or_404(Company, pk=company_id)
    if not request.user.roles.filter(role='recruiter', company=company, is_active=True).exists():
        messages.error(request, 'You do not have access to that company.')
        return redirect(RECRUIT_DASHBOARD)
    request.session['company_id'] = company.id
    messages.success(request, f'Switched to {company.name}.')
    return redirect(RECRUIT_DASHBOARD)


def validate_company_email(email, website):
    if not email or not website:
        return True
    from urllib.parse import urlparse
    parsed = urlparse(website)
    domain = parsed.netloc or parsed.path
    domain = domain.lower().removeprefix('www.')
    email_domain = email.split('@')[-1].lower()
    return email_domain == domain or email_domain == f'www.{domain}'


def add_company(request):
    if not request.user.is_authenticated:
        return redirect(RECRUIT_LOGIN)
    if not request.user.roles.filter(role='recruiter', is_active=True).exists():
        return redirect(RECRUIT_LOGIN)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        website = request.POST.get('website', '').strip()
        email = request.POST.get('email', '').strip()

        if not name:
            messages.error(request, 'Company name is required.')
            return redirect('recruitpanel:add_company')

        if email and website and not validate_company_email(email, website):
            messages.error(request, 'Email domain must match the website domain.')
            return redirect('recruitpanel:add_company')

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
            website=website,
            email=email,
            address=request.POST.get('address', '').strip(),
            summary=request.POST.get('summary', '').strip(),
        )

        UserRole.objects.create(
            user=request.user,
            role='recruiter',
            company=company,
            sub_role='admin',
            is_active=True,
        )

        request.session['company_id'] = company.id
        messages.success(request, f'Company "{name}" created and selected.')
        return redirect(RECRUIT_DASHBOARD)

    return render(request, 'recruitpanel/company_form.html')


@recruiter_required
def company_detail(request):
    company = request.company
    if not company:
        messages.error(request, 'No company selected.')
        return redirect(RECRUIT_DASHBOARD)
    return render(request, 'recruitpanel/company_detail.html', {'company': company})


@recruiter_required
def company_edit(request):
    company = request.company
    if not company:
        messages.error(request, 'No company selected.')
        return redirect(RECRUIT_DASHBOARD)

    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        website = request.POST.get('website', '').strip()
        email = request.POST.get('email', '').strip()
        address = request.POST.get('address', '').strip()
        summary = request.POST.get('summary', '').strip()

        if not name:
            messages.error(request, 'Company name is required.')
            return redirect('recruitpanel:company_edit')

        CompanyEditRequest.objects.create(
            company=company,
            requested_by=request.user,
            name=name,
            website=website,
            email=email,
            address=address,
            summary=summary,
        )
        messages.success(request, 'Your changes have been submitted for admin review.')
        return redirect('recruitpanel:company_detail')

    return render(request, 'recruitpanel/company_form.html', {
        'company': company,
        'editing': True,
    })


# ── Registration ──

def register_company(request):
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        name = request.POST.get('name', '').strip()

        if not phone or not name:
            messages.error(request, 'Phone number and company name are required.')
            return redirect('recruitpanel:register')

        if UserAuth.objects.filter(phone=phone).exists():
            messages.error(request, 'This phone number is already registered.')
            return redirect('recruitpanel:register')

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
            website=request.POST.get('website', '').strip(),
            email=request.POST.get('email', '').strip(),
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

        messages.success(request, f'Company "{name}" registered! Your login PIN is <strong>{pin}</strong>.')
        return redirect(RECRUIT_DASHBOARD)

    return render(request, 'recruitpanel/register.html')


# ── User Management ──

@recruiter_required
def user_list(request):
    users = UserRole.objects.filter(
        company=request.company,
        role='recruiter',
    ).select_related('user', 'user__auth')
    return render(request, 'recruitpanel/user_list.html', {
        'users': users,
        'company': request.company,
    })


@recruiter_required
def user_create(request):
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        name = request.POST.get('name', '').strip()
        sub_role = request.POST.get('sub_role', 'recruiter')

        if not phone or not name:
            messages.error(request, 'Phone and name are required.')
            return redirect('recruitpanel:user_create')

        if UserAuth.objects.filter(phone=phone).exists():
            messages.error(request, 'This phone number is already registered.')
            return redirect('recruitpanel:user_create')

        username = phone
        base_username = username
        counter = 1
        while User.objects.filter(username=username).exists():
            username = f'{base_username}-{counter}'
            counter += 1

        pin = phone[-4:]
        secretname = re.sub(r'[^a-z0-9]', '', name.lower())[:20] or 'user'

        user = User.objects.create_user(username=username)
        user_auth = UserAuth.objects.create(user=user, phone=phone, secretname=secretname)
        user_auth.set_pin(pin)
        user_auth.save()

        UserRole.objects.create(
            user=user,
            role='recruiter',
            company=request.company,
            sub_role=sub_role,
            is_active=True,
        )

        messages.success(request, f'User "{name}" created. PIN is <strong>{pin}</strong>.')
        return redirect('recruitpanel:user_list')

    return render(request, 'recruitpanel/user_form.html', {
        'company': request.company,
    })


# ── Board (Kanban) ──

@recruiter_required
def board(request):
    stages = Stage.objects.filter(company=request.company)
    columns = []
    first_pos = JobPosition.objects.filter(company=request.company, is_active=True).first()
    auto_objs = {}
    if first_pos:
        auto_objs = {a.stage: a.description for a in Automation.objects.filter(company=request.company, position=first_pos)}
    automations = []
    for s in stages:
        apps = Application.objects.filter(company=request.company, status=s.key).select_related('candidate').prefetch_related('candidate__candidate_skills__skill')
        columns.append({'key': s.key, 'label': s.label, 'applications': apps})
        desc = auto_objs.get(s.key, DEFAULT_AUTOMATIONS.get(s.key, ''))
        automations.append({'key': s.key, 'label': s.label, 'description': desc})
    return render(request, 'recruitpanel/board.html', {
        'columns': columns,
        'stages': stages,
        'automations': automations,
        'company': request.company,
    })


# ── Candidates ──

@recruiter_required
def candidate_list(request):
    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    queryset = Application.objects.filter(company=request.company).select_related('candidate').prefetch_related('candidate__candidate_skills__skill')
    if q:
        queryset = queryset.filter(
            models.Q(full_name__icontains=q) |
            models.Q(email__icontains=q) |
            models.Q(position__icontains=q) |
            models.Q(phone__icontains=q)
        )
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    return render(request, 'recruitpanel/candidate_list.html', {
        'candidates': queryset,
        'q': q,
        'status_filter': status_filter,
        'stages': Stage.objects.filter(company=request.company),
        'company': request.company,
    })


@recruiter_required
def candidate_detail(request, pk):
    application = get_object_or_404(Application, company=request.company, pk=pk)
    candidate_profile = application.candidate
    skills = []
    if candidate_profile:
        skills = list(candidate_profile.candidate_skills.select_related('skill').all())
    return render(request, 'recruitpanel/candidate_detail.html', {
        'candidate': application,
        'candidate_profile': candidate_profile,
        'skills': skills,
        'company': request.company,
    })


@recruiter_required
def candidate_create(request):
    if request.method == 'POST':
        try:
            app = Application.objects.create(
                company=request.company,
                full_name=request.POST.get('full_name', '').strip(),
                email=request.POST.get('email', '').strip(),
                phone=request.POST.get('phone', '').strip(),
                position=request.POST.get('position', '').strip(),
                experience=int(request.POST.get('experience', 0)),
                resume=request.FILES.get('resume'),
                cover_letter=request.POST.get('cover_letter', '').strip(),
                status=request.POST.get('status', 'new'),
            )
            messages.success(request, f'{app.full_name} added.')
            return redirect(RECRUIT_CANDIDATES)
        except (ValueError, TypeError) as e:
            messages.error(request, str(e))
    return render(request, 'recruitpanel/candidate_form.html', {
        'candidate': None,
        'stages': Stage.objects.filter(company=request.company),
        'company': request.company,
    })


@recruiter_required
def candidate_edit(request, pk):
    candidate = get_object_or_404(Application, company=request.company, pk=pk)
    if request.method == 'POST':
        try:
            candidate.full_name = request.POST.get('full_name', '').strip()
            candidate.email = request.POST.get('email', '').strip()
            candidate.phone = request.POST.get('phone', '').strip()
            candidate.position = request.POST.get('position', '').strip()
            candidate.experience = int(request.POST.get('experience', 0))
            candidate.cover_letter = request.POST.get('cover_letter', '').strip()
            candidate.status = request.POST.get('status', candidate.status)
            if request.FILES.get('resume'):
                candidate.resume = request.FILES['resume']
            candidate.save()
            messages.success(request, f'{candidate.full_name} updated.')
            return redirect(RECRUIT_CANDIDATES)
        except (ValueError, TypeError) as e:
            messages.error(request, str(e))
    return render(request, 'recruitpanel/candidate_form.html', {
        'candidate': candidate,
        'stages': Stage.objects.filter(company=request.company),
        'company': request.company,
    })


@recruiter_required
def candidate_delete(request, pk):
    candidate = get_object_or_404(Application, company=request.company, pk=pk)
    if request.method == 'POST':
        name = candidate.full_name
        candidate.delete()
        messages.success(request, f'{name} deleted.')
        return redirect(RECRUIT_CANDIDATES)
    return render(request, 'recruitpanel/candidate_confirm_delete.html', {
        'candidate': candidate,
        'company': request.company,
    })


# ── Job Positions ──

@recruiter_required
def job_positions(request):
    positions = JobPosition.objects.filter(company=request.company)
    return render(request, 'recruitpanel/job_positions.html', {
        'positions': positions,
        'company': request.company,
    })


@recruiter_required
def job_position_add(request):
    companies = Company.objects.filter(is_active=True).order_by('name')

    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, 'Title is required.')
            return render(request, 'recruitpanel/job_position_form.html', {
                'position': None,
                'company': request.company,
                'companies': companies,
            })

        company_id = request.POST.get('company')
        if company_id == '__new__':
            new_name = request.POST.get('new_company_name', '').strip()
            if not new_name:
                messages.error(request, 'Company name is required for a new company.')
                return render(request, 'recruitpanel/job_position_form.html', {
                    'position': None,
                    'company': request.company,
                    'companies': companies,
                })
            slug = re.sub(r'[^a-z0-9-]+', '-', new_name.lower()).strip('-')
            original_slug = slug
            counter = 1
            while Company.objects.filter(slug=slug).exists():
                slug = f'{original_slug}-{counter}'
                counter += 1
            target_company = Company.objects.create(
                name=new_name,
                slug=slug,
                website=request.POST.get('new_company_website', '').strip(),
                email=request.POST.get('new_company_email', '').strip(),
                address=request.POST.get('new_company_address', '').strip(),
                summary=request.POST.get('new_company_summary', '').strip(),
            )
            messages.success(request, f'Company "{new_name}" created.')
        elif company_id:
            target_company = get_object_or_404(Company, pk=company_id)
        else:
            target_company = request.company

        position = JobPosition.objects.create(
            company=target_company,
            title=title,
            description=request.POST.get('description', '').strip(),
            base_salary=request.POST.get('base_salary') or None,
            hourly_rate=request.POST.get('hourly_rate') or None,
            location=request.POST.get('location', '').strip(),
            requirements=request.POST.get('requirements', '').strip(),
            is_active=request.POST.get('is_active') == 'on',
        )
        messages.success(request, f'"{position.title}" created for {target_company.name}.')
        return redirect('recruitpanel:job_position_detail', pk=position.pk)

    return render(request, 'recruitpanel/job_position_form.html', {
        'position': None,
        'company': request.company,
        'companies': companies,
    })


@recruiter_required
def job_position_detail(request, pk):
    position = get_object_or_404(JobPosition, pk=pk)
    stages = Stage.objects.filter(company=request.company)
    columns = []
    for s in stages:
        apps = Application.objects.filter(company=request.company, position=position.title, status=s.key)
        columns.append({'key': s.key, 'label': s.label, 'applications': apps})

    auto_objs = {a.stage: a.description for a in Automation.objects.filter(company=request.company, position=position)}
    automations = []
    for s in stages:
        desc = auto_objs.get(s.key, DEFAULT_AUTOMATIONS.get(s.key, ''))
        automations.append({'key': s.key, 'label': s.label, 'description': desc})

    return render(request, 'recruitpanel/job_position_detail.html', {
        'position': position,
        'columns': columns,
        'stages': stages,
        'total_apps': Application.objects.filter(company=request.company, position=position.title).count(),
        'automations': automations,
        'company': request.company,
    })


@recruiter_required
def job_position_edit(request, pk):
    position = get_object_or_404(JobPosition, company=request.company, pk=pk)
    if request.method == 'POST':
        position.description = request.POST.get('description', '').strip()
        position.base_salary = request.POST.get('base_salary') or None
        position.hourly_rate = request.POST.get('hourly_rate') or None
        position.location = request.POST.get('location', '').strip()
        position.requirements = request.POST.get('requirements', '').strip()
        position.is_active = request.POST.get('is_active') == 'on'
        position.save()
        messages.success(request, f'"{position.title}" updated.')
        return redirect('recruitpanel:job_position_detail', pk=position.pk)
    return render(request, 'recruitpanel/job_position_form.html', {
        'position': position,
        'company': request.company,
    })


@recruiter_required
def job_position_delete(request, pk):
    pos = get_object_or_404(JobPosition, company=request.company, pk=pk)
    if request.method == 'POST':
        pos.delete()
        messages.success(request, f'"{pos.title}" deleted.')
    return redirect(RECRUIT_POSITIONS)


# ── Pipeline ──

@recruiter_required
def pipeline(request):
    stages = Stage.objects.filter(company=request.company)
    automations = []
    for s in stages:
        desc = DEFAULT_AUTOMATIONS.get(s.key, '')
        automations.append({'key': s.key, 'label': s.label, 'description': desc})
    return render(request, 'recruitpanel/pipeline.html', {
        'automations': automations,
        'stages': stages,
        'company': request.company,
    })


@recruiter_required
def add_stage(request):
    if request.method == 'POST':
        label = request.POST.get('label', '').strip()
        after_key = request.POST.get('after', '')
        if not label:
            return JsonResponse({'success': False, 'error': 'Label is required'})
        key = label.lower().replace(' ', '_').replace('-', '_')
        orig_key = key
        n = 1
        while Stage.objects.filter(company=request.company, key=key).exists():
            key = f'{orig_key}_{n}'
            n += 1
        if after_key:
            try:
                after = Stage.objects.get(company=request.company, key=after_key)
                order = after.order + 1
                Stage.objects.filter(company=request.company, order__gte=order).update(order=models.F('order') + 1)
            except Stage.DoesNotExist:
                order = Stage.objects.filter(company=request.company).count()
        else:
            order = Stage.objects.filter(company=request.company).count()
        Stage.objects.create(company=request.company, key=key, label=label, order=order)
        for pos in JobPosition.objects.filter(company=request.company):
            Automation.objects.get_or_create(company=request.company, position=pos, stage=key)
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=405)


@recruiter_required
def delete_stage(request, stage_key):
    if request.method == 'POST':
        stage = get_object_or_404(Stage, company=request.company, key=stage_key)
        stage.delete()
        Automation.objects.filter(company=request.company, stage=stage_key).delete()
        Application.objects.filter(company=request.company, status=stage_key).update(status='new')
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=405)


@recruiter_required
def update_global_automation(request, stage):
    if request.method == 'POST':
        desc = request.POST.get('description', '').strip()
        count = 0
        for pos in JobPosition.objects.filter(company=request.company):
            auto, _ = Automation.objects.get_or_create(
                company=request.company,
                position=pos,
                stage=stage,
            )
            auto.description = desc
            auto.save()
            count += 1
        return JsonResponse({'success': True, 'updated': count})
    return JsonResponse({'success': False}, status=405)


@recruiter_required
def update_automation(request, position_pk, stage):
    if request.method == 'POST':
        position = get_object_or_404(JobPosition, company=request.company, pk=position_pk)
        desc = request.POST.get('description', '').strip()
        auto, _ = Automation.objects.get_or_create(
            company=request.company,
            position=position,
            stage=stage,
        )
        auto.description = desc
        auto.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=405)


# ── Panelist & Screenings ──

@recruiter_required
def panelist(request):
    return render(request, 'recruitpanel/panelist.html', {'company': request.company})


@recruiter_required
def screenings(request):
    q = request.GET.get('q', '').strip()
    stage_filter = request.GET.get('status', '')
    position_filter = request.GET.get('position', '')
    panelist_filter = request.GET.get('panelist', '')

    queryset = Application.objects.filter(company=request.company).select_related(
        'candidate'
    ).prefetch_related(
        models.Prefetch('screenings', queryset=Screening.objects.select_related('panelist'))
    )

    if q:
        queryset = queryset.filter(
            models.Q(full_name__icontains=q) |
            models.Q(position__icontains=q) |
            models.Q(email__icontains=q)
        )
    if stage_filter:
        queryset = queryset.filter(status=stage_filter)
    if position_filter:
        try:
            pos = JobPosition.objects.get(id=position_filter)
            queryset = queryset.filter(position=pos.title)
        except JobPosition.DoesNotExist:
            pass
    if panelist_filter:
        queryset = queryset.filter(screenings__panelist_id=panelist_filter)

    current_dt = now()
    today_start = current_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    scheduled_today = Screening.objects.filter(
        company=request.company,
        scheduled_at__gte=today_start, scheduled_at__lt=today_end,
        status='scheduled'
    ).count()
    in_progress = Screening.objects.filter(
        company=request.company, status='in_progress'
    ).count()

    thirty_days_ago = current_dt - timedelta(days=30)
    completed_30d = Screening.objects.filter(
        company=request.company,
        status__in=('passed', 'failed'),
        updated_at__gte=thirty_days_ago
    )
    total_completed = completed_30d.count()
    passed_30d = completed_30d.filter(status='passed').count()
    pass_rate = round(passed_30d / total_completed * 100) if total_completed > 0 else 0

    positions = JobPosition.objects.filter(company=request.company, is_active=True)
    panelists = Panelist.objects.filter(company=request.company, is_active=True)
    stages = Stage.objects.filter(company=request.company)

    return render(request, 'recruitpanel/screenings.html', {
        'screenings': queryset,
        'scheduled_today': scheduled_today,
        'in_progress': in_progress,
        'pass_rate': pass_rate,
        'positions': positions,
        'panelists': panelists,
        'screening_statuses': Screening.STATUS_CHOICES,
        'stages': stages,
        'q': q,
        'status_filter': stage_filter,
        'position_filter': position_filter,
        'panelist_filter': panelist_filter,
        'company': request.company,
    })
