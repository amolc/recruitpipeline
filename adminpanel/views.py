from functools import wraps
import re
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import models
from django.http import JsonResponse, Http404
from django.db.models import Count
from django.utils.timezone import now
from company.models import Company, CompanyEditRequest
from api.models import Application, JobPosition, Automation, DEFAULT_AUTOMATIONS, Stage, UserProfile, seed_default_stages

User = get_user_model()


def company_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        if request.company:
            return redirect('admin_login', company_slug=request.company.slug)
        return redirect('landing')
    return wrapper


def login_view(request, company_slug=None):
    if not request.company:
        raise Http404('Company not found')
    if request.user.is_authenticated:
        if request.user.is_superuser or request.user.profile.company == request.company:
            return redirect('candidate_list', company_slug=company_slug)
    error = None
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username', ''),
            password=request.POST.get('password', ''),
        )
        if user:
            if user.is_superuser or (hasattr(user, 'profile') and user.profile.company == request.company):
                login(request, user)
                return redirect('candidate_list', company_slug=company_slug)
            error = 'You do not have access to this company.'
        else:
            error = 'Invalid username or password.'
    return render(request, 'adminpanel/login.html', {
        'error': error,
        'company': request.company,
    })


def logout_view(request, company_slug=None):
    logout(request)
    return redirect('admin_login', company_slug=company_slug if company_slug else request.company.slug)


@company_login_required
def board(request, company_slug=None):
    stages = Stage.objects.filter(company=request.company)
    if not stages.exists():
        seed_default_stages(request.company)
        stages = Stage.objects.filter(company=request.company)
    columns = []
    first_pos = JobPosition.objects.filter(company=request.company, is_active=True).first()
    auto_objs = {}
    if first_pos:
        auto_objs = {a.stage: a.description for a in Automation.objects.filter(company=request.company, position=first_pos)}
    automations = []
    for s in stages:
        apps = Application.objects.filter(company=request.company, status=s.key)
        columns.append({'key': s.key, 'label': s.label, 'applications': apps})
        desc = auto_objs.get(s.key, DEFAULT_AUTOMATIONS.get(s.key, ''))
        automations.append({'key': s.key, 'label': s.label, 'description': desc})
    return render(request, 'adminpanel/board.html', {
        'columns': columns,
        'stages': stages,
        'automations': automations,
        'company': request.company,
    })


@company_login_required
def job_positions(request, company_slug=None):
    positions = JobPosition.objects.filter(company=request.company)
    return render(request, 'adminpanel/job_positions.html', {
        'positions': positions,
        'company': request.company,
    })


@company_login_required
def job_position_add(request, company_slug=None):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if title:
            JobPosition.objects.get_or_create(
                company=request.company,
                title=title,
                defaults={'company': request.company},
            )
            messages.success(request, f'"{title}" added.')
        else:
            messages.error(request, 'Title cannot be empty.')
    return redirect('job_positions', company_slug=company_slug)


@company_login_required
def job_position_detail(request, pk, company_slug=None):
    position = get_object_or_404(JobPosition, company=request.company, pk=pk)
    stages = Stage.objects.filter(company=request.company)
    if not stages.exists():
        seed_default_stages(request.company)
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

    return render(request, 'adminpanel/job_position_detail.html', {
        'position': position,
        'columns': columns,
        'stages': stages,
        'total_apps': Application.objects.filter(company=request.company, position=position.title).count(),
        'automations': automations,
        'company': request.company,
    })


@company_login_required
def job_position_edit(request, pk, company_slug=None):
    position = get_object_or_404(JobPosition, company=request.company, pk=pk)
    if request.method == 'POST':
        position.description = request.POST.get('description', '').strip()
        position.base_salary = request.POST.get('base_salary') or None
        position.hourly_rate = request.POST.get('hourly_rate') or None
        position.salary_max = request.POST.get('salary_max') or None
        position.location = request.POST.get('location', '').strip()
        position.employment_type = request.POST.get('employment_type', 'full_time')
        position.work_type = request.POST.get('work_type', 'on_site')
        position.experience_required = request.POST.get('experience_required') or None
        position.requirements = request.POST.get('requirements', '').strip()
        position.is_active = request.POST.get('is_active') == 'on'
        position.save()
        messages.success(request, f'"{position.title}" updated.')
        return redirect('job_position_detail', company_slug=company_slug, pk=position.pk)
    return render(request, 'adminpanel/job_position_form.html', {
        'position': position,
        'company': request.company,
    })


@company_login_required
def job_position_delete(request, pk, company_slug=None):
    pos = get_object_or_404(JobPosition, company=request.company, pk=pk)
    if request.method == 'POST':
        pos.delete()
        messages.success(request, f'"{pos.title}" deleted.')
    return redirect('job_positions', company_slug=company_slug)


@company_login_required
def panelist(request, company_slug=None):
    return render(request, 'adminpanel/panelist.html', {'company': request.company})


@company_login_required
def screenings(request, company_slug=None):
    return render(request, 'adminpanel/screenings.html', {'company': request.company})


@company_login_required
def candidate_list(request, company_slug=None):
    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    queryset = Application.objects.filter(company=request.company)
    if q:
        queryset = queryset.filter(
            models.Q(full_name__icontains=q) |
            models.Q(email__icontains=q) |
            models.Q(position__icontains=q) |
            models.Q(phone__icontains=q)
        )
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    return render(request, 'adminpanel/candidate_list.html', {
        'candidates': queryset,
        'q': q,
        'status_filter': status_filter,
        'stages': Stage.objects.filter(company=request.company),
        'company': request.company,
    })


@company_login_required
def candidate_detail(request, pk, company_slug=None):
    candidate = get_object_or_404(Application, company=request.company, pk=pk)
    return render(request, 'adminpanel/candidate_detail.html', {
        'candidate': candidate,
        'company': request.company,
    })


@company_login_required
def candidate_create(request, company_slug=None):
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
            return redirect('candidate_list', company_slug=company_slug)
        except (ValueError, TypeError) as e:
            messages.error(request, str(e))
    return render(request, 'adminpanel/candidate_form.html', {
        'candidate': None,
        'stages': Stage.objects.filter(company=request.company),
        'company': request.company,
    })


@company_login_required
def candidate_edit(request, pk, company_slug=None):
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
            return redirect('candidate_list', company_slug=company_slug)
        except (ValueError, TypeError) as e:
            messages.error(request, str(e))
    return render(request, 'adminpanel/candidate_form.html', {
        'candidate': candidate,
        'stages': Stage.objects.filter(company=request.company),
        'company': request.company,
    })


@company_login_required
def candidate_delete(request, pk, company_slug=None):
    candidate = get_object_or_404(Application, company=request.company, pk=pk)
    if request.method == 'POST':
        name = candidate.full_name
        candidate.delete()
        messages.success(request, f'{name} deleted.')
        return redirect('candidate_list', company_slug=company_slug)
    return render(request, 'adminpanel/candidate_confirm_delete.html', {
        'candidate': candidate,
        'company': request.company,
    })


@company_login_required
def approve_candidate(request, pk, company_slug=None):
    candidate = get_object_or_404(Application, company=request.company, pk=pk)
    if candidate.status == 'new' and request.method == 'POST':
        candidate.status = 'screening'
        candidate.save()
        messages.success(request, f'{candidate.full_name} approved and moved to Screening.')
    else:
        messages.error(request, 'Candidate cannot be approved.')
    return redirect('candidate_list', company_slug=company_slug)


@company_login_required
def pipeline(request, company_slug=None):
    stages = Stage.objects.filter(company=request.company)
    if not stages.exists():
        seed_default_stages(request.company)
        stages = Stage.objects.filter(company=request.company)
    pipeline_stages = stages.exclude(key='new')
    columns = []
    first_pos = JobPosition.objects.filter(company=request.company, is_active=True).first()
    auto_objs = {}
    if first_pos:
        auto_objs = {a.stage: a.description for a in Automation.objects.filter(company=request.company, position=first_pos)}
    automations = []
    for s in stages:
        desc = auto_objs.get(s.key, DEFAULT_AUTOMATIONS.get(s.key, ''))
        automations.append({'key': s.key, 'label': s.label, 'description': desc})
    for s in pipeline_stages:
        apps = Application.objects.filter(company=request.company, status=s.key)
        columns.append({'key': s.key, 'label': s.label, 'applications': apps})
    return render(request, 'adminpanel/pipeline.html', {
        'automations': automations,
        'stages': stages,
        'pipeline_stages': pipeline_stages,
        'columns': columns,
        'company': request.company,
    })


@company_login_required
def add_stage(request, company_slug=None):
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


@company_login_required
def delete_stage(request, stage_key, company_slug=None):
    if request.method == 'POST':
        stage = get_object_or_404(Stage, company=request.company, key=stage_key)
        stage.delete()
        Automation.objects.filter(company=request.company, stage=stage_key).delete()
        Application.objects.filter(company=request.company, status=stage_key).update(status='new')
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=405)


@company_login_required
def update_global_automation(request, stage, company_slug=None):
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


@company_login_required
def update_automation(request, position_pk, stage, company_slug=None):
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


def company_home(request, company_slug=None):
    if not request.company:
        raise Http404('Company not found')
    if request.user.is_authenticated:
        return redirect('candidate_list', company_slug=company_slug)
    return redirect('admin_login', company_slug=company_slug)


# ── Super Admin ──────────

def super_login_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('landing')
        if not request.user.is_superuser:
            raise Http404('Super admin access required')
        return view_func(request, *args, **kwargs)
    return wrapper


@super_login_required
def super_dashboard(request):
    stats = {
        'companies': Company.objects.count(),
        'candidates': Application.objects.count(),
        'positions': JobPosition.objects.count(),
        'users': User.objects.count(),
        'stages': Stage.objects.count(),
    }
    recent = Application.objects.select_related('company').order_by('-submitted_at')[:10]
    return render(request, 'adminpanel/super/dashboard.html', {
        'stats': stats,
        'recent': recent,
    })


@super_login_required
def super_companies(request):
    companies = Company.objects.annotate(
        candidate_count=Count('applications'),
        position_count=Count('job_positions'),
        user_count=Count('members'),
    ).order_by('-created_at')
    return render(request, 'adminpanel/super/companies.html', {'companies': companies})


@super_login_required
def super_company_create(request):
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
                address=request.POST.get('address', '').strip(),
                summary=request.POST.get('summary', '').strip(),
            )
            if request.FILES.get('logo'):
                company.logo = request.FILES['logo']
                company.save()
            messages.success(request, f'Company "{name}" created.')
            return redirect('super_companies')
        else:
            messages.error(request, 'Company name is required.')
    return render(request, 'adminpanel/super/company_form.html', {'company': None})


@super_login_required
def super_company_edit(request, pk):
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
        company.logo_url = request.POST.get('logo_url', '').strip()
        if request.FILES.get('logo'):
            company.logo = request.FILES['logo']
        company.address = request.POST.get('address', '').strip()
        company.summary = request.POST.get('summary', '').strip()
        company.is_active = request.POST.get('is_active') == 'on'
        company.save()
        messages.success(request, f'Company "{company.name}" updated.')
        return redirect('super_companies')
    return render(request, 'adminpanel/super/company_form.html', {'company': company})


@super_login_required
def super_company_detail(request, pk):
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
    return render(request, 'adminpanel/super/company_detail.html', {
        'company': company,
        'candidates': candidates,
        'positions': positions,
        'members': members,
        'stats': stats,
    })


@super_login_required
def super_candidates(request):
    q = request.GET.get('q', '').strip()
    company_filter = request.GET.get('company', '')
    candidates = Application.objects.select_related('company')
    if q:
        candidates = candidates.filter(
            models.Q(full_name__icontains=q) |
            models.Q(email__icontains=q) |
            models.Q(position__icontains=q)
        )
    if company_filter:
        candidates = candidates.filter(company__slug=company_filter)
    candidates = candidates.order_by('-submitted_at')
    companies = Company.objects.filter(is_active=True)
    return render(request, 'adminpanel/super/candidates.html', {
        'candidates': candidates,
        'companies': companies,
        'q': q,
        'company_filter': company_filter,
    })


@super_login_required
def super_positions(request):
    company_filter = request.GET.get('company', '')
    positions = JobPosition.objects.select_related('company')
    if company_filter:
        positions = positions.filter(company__slug=company_filter)
    positions = positions.order_by('company__name', 'title')
    companies = Company.objects.filter(is_active=True)
    return render(request, 'adminpanel/super/positions.html', {
        'positions': positions,
        'companies': companies,
        'company_filter': company_filter,
    })


@super_login_required
def super_users(request):
    users = User.objects.order_by('-is_superuser', 'username')
    profiles = {
        up.user_id: up
        for up in UserProfile.objects.select_related('company').all()
    }
    user_list = []
    for u in users:
        up = profiles.get(u.id)
        user_list.append({
            'user': u,
            'company': up.company if up else None,
            'role': up.role if up else None,
        })
    return render(request, 'adminpanel/super/users.html', {'user_list': user_list})


@super_login_required
def super_user_create(request):
    companies = Company.objects.filter(is_active=True)
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '').strip()
        company_id = request.POST.get('company')
        role = request.POST.get('role', 'recruiter')
        is_superuser = request.POST.get('is_superuser') == 'on'
        if username and password and company_id:
            if User.objects.filter(username=username).exists():
                messages.error(request, f'User "{username}" already exists.')
            else:
                user = User.objects.create_user(
                    username=username,
                    password=password,
                    is_superuser=is_superuser,
                )
                company = Company.objects.get(id=company_id)
                UserProfile.objects.create(user=user, company=company, role=role)
                messages.success(request, f'User "{username}" created for {company.name}.')
                return redirect('super_users')
        else:
            messages.error(request, 'Username, password, and company are required.')
    return render(request, 'adminpanel/super/user_form.html', {'companies': companies, 'user_obj': None})


# ── Edit Requests ──

@super_login_required
def super_edit_requests(request):
    status_filter = request.GET.get('status', 'pending')
    requests_qs = CompanyEditRequest.objects.select_related('company', 'requested_by', 'reviewed_by')
    if status_filter in ('pending', 'approved', 'rejected'):
        requests_qs = requests_qs.filter(status=status_filter)
    return render(request, 'adminpanel/super/edit_requests.html', {
        'edit_requests': requests_qs,
        'status_filter': status_filter,
    })


@super_login_required
def super_edit_request_detail(request, pk):
    edit_request = get_object_or_404(
        CompanyEditRequest.objects.select_related('company', 'requested_by', 'reviewed_by'), pk=pk,
    )
    return render(request, 'adminpanel/super/edit_request_detail.html', {
        'edit_request': edit_request,
    })


@super_login_required
def super_edit_request_approve(request, pk):
    if request.method != 'POST':
        return redirect('super_edit_requests')
    edit_request = get_object_or_404(CompanyEditRequest, pk=pk, status='pending')
    company = edit_request.company
    if edit_request.name:
        company.name = edit_request.name
    if edit_request.website:
        company.website = edit_request.website
    if edit_request.email:
        company.email = edit_request.email
    if edit_request.address:
        company.address = edit_request.address
    if edit_request.summary:
        company.summary = edit_request.summary
    if edit_request.brand_color:
        company.brand_color = edit_request.brand_color
    if edit_request.logo:
        company.logo = edit_request.logo
    company.save()
    edit_request.status = 'approved'
    edit_request.reviewed_by = request.user
    edit_request.reviewed_at = now()
    edit_request.save()
    messages.success(request, f'Edit request for "{company.name}" approved and applied.')
    return redirect('super_edit_requests')


@super_login_required
def super_edit_request_reject(request, pk):
    if request.method != 'POST':
        return redirect('super_edit_requests')
    edit_request = get_object_or_404(CompanyEditRequest, pk=pk, status='pending')
    edit_request.status = 'rejected'
    edit_request.reviewed_by = request.user
    edit_request.reviewed_at = now()
    edit_request.save()
    messages.success(request, f'Edit request for "{edit_request.company.name}" rejected.')
    return redirect('super_edit_requests')
