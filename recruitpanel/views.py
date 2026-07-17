from functools import wraps
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.db import models
from django.http import JsonResponse, Http404
from django.db.models import Count
from api.models import Application, JobPosition, Automation, DEFAULT_AUTOMATIONS, Stage, Company, UserRole

RECRUIT_LOGIN = 'recruitpanel:recruitpanel_login'
RECRUIT_DASHBOARD = 'recruitpanel:recruitpanel_dashboard'
RECRUIT_CANDIDATES = 'recruitpanel:candidate_list'
RECRUIT_POSITIONS = 'recruitpanel:job_positions'
RECRUIT_BOARD = 'recruitpanel:board'


def recruiter_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(RECRUIT_LOGIN, company_slug=kwargs.get('company_slug'))
        if not request.user.roles.filter(role='recruiter', company=request.company, is_active=True).exists():
            return redirect(RECRUIT_LOGIN, company_slug=kwargs.get('company_slug'))
        return view_func(request, *args, **kwargs)
    return wrapper


def login_view(request, company_slug=None):
    company = get_object_or_404(Company, slug=company_slug)

    if request.user.is_authenticated:
        if request.user.roles.filter(role='recruiter', company=company, is_active=True).exists():
            return redirect(RECRUIT_DASHBOARD, company_slug=company_slug)
        logout(request)

    error = None
    if request.method == 'POST':
        phone = request.POST.get('phone', '').strip()
        pin = request.POST.get('pin', '').strip()
        user = authenticate(request, phone=phone, pin=pin)
        if user and user.roles.filter(role='recruiter', company=company, is_active=True).exists():
            login(request, user)
            request.session['role'] = 'recruiter'
            request.session['company_id'] = company.id
            return redirect(RECRUIT_DASHBOARD, company_slug=company_slug)
        if user:
            error = 'You do not have access to this company panel.'
        else:
            error = 'Invalid phone or PIN.'

    return render(request, 'recruitpanel/login.html', {
        'error': error,
        'company': company,
    })


@recruiter_required
def dashboard(request, company_slug=None):
    company = request.company
    stats = {
        'candidates': Application.objects.filter(company=company).count(),
        'positions': JobPosition.objects.filter(company=company).count(),
        'active_positions': JobPosition.objects.filter(company=company, is_active=True).count(),
    }
    return render(request, 'recruitpanel/dashboard.html', {
        'stats': stats,
        'company': company,
    })


def logout_view(request, company_slug=None):
    logout(request)
    return redirect(RECRUIT_LOGIN, company_slug=company_slug)


# ── Board (Kanban) ──

@recruiter_required
def board(request, company_slug=None):
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
    return render(request, 'recruitpanel/board.html', {
        'columns': columns,
        'stages': stages,
        'automations': automations,
        'company': request.company,
    })


# ── Candidates ──

@recruiter_required
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
    return render(request, 'recruitpanel/candidate_list.html', {
        'candidates': queryset,
        'q': q,
        'status_filter': status_filter,
        'stages': Stage.objects.filter(company=request.company),
        'company': request.company,
    })


@recruiter_required
def candidate_detail(request, pk, company_slug=None):
    candidate = get_object_or_404(Application, company=request.company, pk=pk)
    return render(request, 'recruitpanel/candidate_detail.html', {
        'candidate': candidate,
        'company': request.company,
    })


@recruiter_required
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
            return redirect(RECRUIT_CANDIDATES, company_slug=company_slug)
        except (ValueError, TypeError) as e:
            messages.error(request, str(e))
    return render(request, 'recruitpanel/candidate_form.html', {
        'candidate': None,
        'stages': Stage.objects.filter(company=request.company),
        'company': request.company,
    })


@recruiter_required
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
            return redirect(RECRUIT_CANDIDATES, company_slug=company_slug)
        except (ValueError, TypeError) as e:
            messages.error(request, str(e))
    return render(request, 'recruitpanel/candidate_form.html', {
        'candidate': candidate,
        'stages': Stage.objects.filter(company=request.company),
        'company': request.company,
    })


@recruiter_required
def candidate_delete(request, pk, company_slug=None):
    candidate = get_object_or_404(Application, company=request.company, pk=pk)
    if request.method == 'POST':
        name = candidate.full_name
        candidate.delete()
        messages.success(request, f'{name} deleted.')
        return redirect(RECRUIT_CANDIDATES, company_slug=company_slug)
    return render(request, 'recruitpanel/candidate_confirm_delete.html', {
        'candidate': candidate,
        'company': request.company,
    })


# ── Job Positions ──

@recruiter_required
def job_positions(request, company_slug=None):
    positions = JobPosition.objects.filter(company=request.company)
    return render(request, 'recruitpanel/job_positions.html', {
        'positions': positions,
        'company': request.company,
    })


@recruiter_required
def job_position_add(request, company_slug=None):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if not title:
            messages.error(request, 'Title is required.')
            return render(request, 'recruitpanel/job_position_form.html', {
                'position': None,
                'company': request.company,
            })
        position = JobPosition.objects.create(
            company=request.company,
            title=title,
            description=request.POST.get('description', '').strip(),
            base_salary=request.POST.get('base_salary') or None,
            hourly_rate=request.POST.get('hourly_rate') or None,
            location=request.POST.get('location', '').strip(),
            requirements=request.POST.get('requirements', '').strip(),
            is_active=request.POST.get('is_active') == 'on',
        )
        messages.success(request, f'"{position.title}" created.')
        return redirect('recruitpanel:job_position_detail', company_slug=company_slug, pk=position.pk)

    return render(request, 'recruitpanel/job_position_form.html', {
        'position': None,
        'company': request.company,
    })


@recruiter_required
def job_position_detail(request, pk, company_slug=None):
    position = get_object_or_404(JobPosition, company=request.company, pk=pk)
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
def job_position_edit(request, pk, company_slug=None):
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
        return redirect('recruitpanel:job_position_detail', company_slug=company_slug, pk=position.pk)
    return render(request, 'recruitpanel/job_position_form.html', {
        'position': position,
        'company': request.company,
    })


@recruiter_required
def job_position_delete(request, pk, company_slug=None):
    pos = get_object_or_404(JobPosition, company=request.company, pk=pk)
    if request.method == 'POST':
        pos.delete()
        messages.success(request, f'"{pos.title}" deleted.')
    return redirect(RECRUIT_POSITIONS, company_slug=company_slug)


# ── Pipeline ──

@recruiter_required
def pipeline(request, company_slug=None):
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


@recruiter_required
def delete_stage(request, stage_key, company_slug=None):
    if request.method == 'POST':
        stage = get_object_or_404(Stage, company=request.company, key=stage_key)
        stage.delete()
        Automation.objects.filter(company=request.company, stage=stage_key).delete()
        Application.objects.filter(company=request.company, status=stage_key).update(status='new')
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=405)


@recruiter_required
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


@recruiter_required
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


# ── Panelist & Screenings (stubs) ──

@recruiter_required
def panelist(request, company_slug=None):
    return render(request, 'recruitpanel/panelist.html', {'company': request.company})


@recruiter_required
def screenings(request, company_slug=None):
    return render(request, 'recruitpanel/screenings.html', {'company': request.company})
