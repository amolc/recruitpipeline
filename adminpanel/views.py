from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.db import models
from django.http import JsonResponse
from api.models import Application, JobPosition, Automation, DEFAULT_AUTOMATIONS, Stage

def login_view(request):
    if request.user.is_authenticated:
        return redirect('candidate_list')
    error = None
    if request.method == 'POST':
        user = authenticate(
            request,
            username=request.POST.get('username', ''),
            password=request.POST.get('password', ''),
        )
        if user:
            login(request, user)
            return redirect('candidate_list')
        error = 'Invalid username or password.'
    return render(request, 'adminpanel/login.html', {'error': error})

def logout_view(request):
    logout(request)
    return redirect('admin_login')

@login_required(login_url='admin_login')
def board(request):
    stages = Stage.objects.all()
    columns = []
    first_pos = JobPosition.objects.filter(is_active=True).first()
    auto_objs = {}
    if first_pos:
        auto_objs = {a.stage: a.description for a in Automation.objects.filter(position=first_pos)}
    automations = []
    for s in stages:
        apps = Application.objects.filter(status=s.key)
        columns.append({'key': s.key, 'label': s.label, 'applications': apps})
        desc = auto_objs.get(s.key, DEFAULT_AUTOMATIONS.get(s.key, ''))
        automations.append({'key': s.key, 'label': s.label, 'description': desc})
    return render(request, 'adminpanel/board.html', {'columns': columns, 'stages': stages, 'automations': automations})

@login_required(login_url='admin_login')
def job_positions(request):
    positions = JobPosition.objects.all()
    return render(request, 'adminpanel/job_positions.html', {'positions': positions})

@login_required(login_url='admin_login')
def job_position_add(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        if title:
            JobPosition.objects.get_or_create(title=title)
            messages.success(request, f'"{title}" added.')
        else:
            messages.error(request, 'Title cannot be empty.')
    return redirect('job_positions')

@login_required(login_url='admin_login')
def job_position_detail(request, pk):
    position = get_object_or_404(JobPosition, pk=pk)
    stages = Stage.objects.all()
    columns = []
    for s in stages:
        apps = Application.objects.filter(position=position.title, status=s.key)
        columns.append({'key': s.key, 'label': s.label, 'applications': apps})

    auto_objs = {a.stage: a.description for a in Automation.objects.filter(position=position)}
    automations = []
    for s in stages:
        desc = auto_objs.get(s.key, DEFAULT_AUTOMATIONS.get(s.key, ''))
        automations.append({'key': s.key, 'label': s.label, 'description': desc})

    return render(request, 'adminpanel/job_position_detail.html', {
        'position': position,
        'columns': columns,
        'stages': stages,
        'total_apps': Application.objects.filter(position=position.title).count(),
        'automations': automations,
    })

@login_required(login_url='admin_login')
def job_position_edit(request, pk):
    position = get_object_or_404(JobPosition, pk=pk)
    if request.method == 'POST':
        position.description = request.POST.get('description', '').strip()
        position.base_salary = request.POST.get('base_salary') or None
        position.hourly_rate = request.POST.get('hourly_rate') or None
        position.location = request.POST.get('location', '').strip()
        position.requirements = request.POST.get('requirements', '').strip()
        position.is_active = request.POST.get('is_active') == 'on'
        position.save()
        messages.success(request, f'"{position.title}" updated.')
        return redirect('job_position_detail', pk=position.pk)
    return render(request, 'adminpanel/job_position_form.html', {'position': position})

@login_required(login_url='admin_login')
def job_position_delete(request, pk):
    pos = get_object_or_404(JobPosition, pk=pk)
    if request.method == 'POST':
        pos.delete()
        messages.success(request, f'"{pos.title}" deleted.')
    return redirect('job_positions')

@login_required(login_url='admin_login')
def panelist(request):
    return render(request, 'adminpanel/panelist.html')

@login_required(login_url='admin_login')
def screenings(request):
    return render(request, 'adminpanel/screenings.html')

# ── Candidate CRUD ──

@login_required(login_url='admin_login')
def candidate_list(request):
    q = request.GET.get('q', '').strip()
    status_filter = request.GET.get('status', '')
    queryset = Application.objects.all()
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
        'stages': Stage.objects.all(),
    })

@login_required(login_url='admin_login')
def candidate_detail(request, pk):
    candidate = get_object_or_404(Application, pk=pk)
    return render(request, 'adminpanel/candidate_detail.html', {'candidate': candidate})

@login_required(login_url='admin_login')
def candidate_create(request):
    if request.method == 'POST':
        try:
            app = Application.objects.create(
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
            return redirect('candidate_list')
        except (ValueError, TypeError) as e:
            messages.error(request, str(e))
    return render(request, 'adminpanel/candidate_form.html', {
        'candidate': None,
        'stages': Stage.objects.all(),
    })

@login_required(login_url='admin_login')
def candidate_edit(request, pk):
    candidate = get_object_or_404(Application, pk=pk)
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
            return redirect('candidate_list')
        except (ValueError, TypeError) as e:
            messages.error(request, str(e))
    return render(request, 'adminpanel/candidate_form.html', {
        'candidate': candidate,
        'stages': Stage.objects.all(),
    })

@login_required(login_url='admin_login')
def candidate_delete(request, pk):
    candidate = get_object_or_404(Application, pk=pk)
    if request.method == 'POST':
        name = candidate.full_name
        candidate.delete()
        messages.success(request, f'{name} deleted.')
        return redirect('candidate_list')
    return render(request, 'adminpanel/candidate_confirm_delete.html', {'candidate': candidate})

@login_required(login_url='admin_login')
def pipeline(request):
    stages = Stage.objects.all()
    automations = []
    for s in stages:
        desc = DEFAULT_AUTOMATIONS.get(s.key, '')
        automations.append({'key': s.key, 'label': s.label, 'description': desc})
    return render(request, 'adminpanel/pipeline.html', {'automations': automations, 'stages': stages})

@login_required(login_url='admin_login')
def add_stage(request):
    if request.method == 'POST':
        label = request.POST.get('label', '').strip()
        after_key = request.POST.get('after', '')
        if not label:
            return JsonResponse({'success': False, 'error': 'Label is required'})
        key = label.lower().replace(' ', '_').replace('-', '_')
        # ensure unique key
        orig_key = key
        n = 1
        while Stage.objects.filter(key=key).exists():
            key = f'{orig_key}_{n}'
            n += 1
        if after_key:
            try:
                after = Stage.objects.get(key=after_key)
                order = after.order + 1
                # shift later stages
                Stage.objects.filter(order__gte=order).update(order=models.F('order') + 1)
            except Stage.DoesNotExist:
                order = Stage.objects.count()
        else:
            order = Stage.objects.count()
        Stage.objects.create(key=key, label=label, order=order)
        # create automation records for all positions
        for pos in JobPosition.objects.all():
            Automation.objects.get_or_create(position=pos, stage=key)
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=405)

@login_required(login_url='admin_login')
def delete_stage(request, stage_key):
    if request.method == 'POST':
        stage = get_object_or_404(Stage, key=stage_key)
        stage.delete()
        # remove automation records
        Automation.objects.filter(stage=stage_key).delete()
        # update applications to 'new'
        Application.objects.filter(status=stage_key).update(status='new')
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=405)

@login_required(login_url='admin_login')
def update_global_automation(request, stage):
    if request.method == 'POST':
        desc = request.POST.get('description', '').strip()
        count = 0
        for pos in JobPosition.objects.all():
            auto, _ = Automation.objects.get_or_create(position=pos, stage=stage)
            auto.description = desc
            auto.save()
            count += 1
        return JsonResponse({'success': True, 'updated': count})
    return JsonResponse({'success': False}, status=405)

@login_required(login_url='admin_login')
def update_automation(request, position_pk, stage):
    if request.method == 'POST':
        position = get_object_or_404(JobPosition, pk=position_pk)
        desc = request.POST.get('description', '').strip()
        auto, _ = Automation.objects.get_or_create(position=position, stage=stage)
        auto.description = desc
        auto.save()
        return JsonResponse({'success': True})
    return JsonResponse({'success': False}, status=405)
