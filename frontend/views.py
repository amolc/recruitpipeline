from functools import wraps
import json
import re
from pathlib import Path
from django.shortcuts import render, get_object_or_404, redirect
from django.http import Http404, JsonResponse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.views.decorators.csrf import csrf_exempt
from company.models import Company
from api.models import JobPosition, UserAuth, UserRole, Candidate, CandidateSkill, Skill

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
        action = request.POST.get('action', '')
        country_code = request.POST.get('country_code', '+91').strip()
        raw_phone = request.POST.get('phone', '').strip()
        phone_with_code = country_code + raw_phone
        pin = request.POST.get('pin', '').strip()

        if action == 'register':
            name = request.POST.get('name', '').strip()
            role_type = request.POST.get('role_type', 'candidate')

            if not name or not raw_phone or not pin:
                error = 'All fields are required.'
            elif UserAuth.objects.filter(phone=phone_with_code).exists():
                error = 'This phone number is already registered. Please sign in.'
            else:
                username = phone_with_code
                base_username = username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f'{base_username}-{counter}'
                    counter += 1

                secretname = re.sub(r'[^a-z0-9]', '', name.lower())[:20] or f'user{raw_phone[-4:]}'
                user = User.objects.create_user(username=username)
                user_auth = UserAuth.objects.create(user=user, phone=phone_with_code, secretname=secretname)
                user_auth.set_pin(pin)
                user_auth.save()

                UserRole.objects.create(
                    user=user,
                    role=role_type,
                    is_active=True,
                )

                if role_type == 'candidate':
                    Candidate.objects.create(
                        user=user,
                        full_name=name,
                        email=user_auth.secretname,
                        phone=phone_with_code,
                    )

                user = authenticate(request, phone=phone_with_code, pin=pin)
                if user:
                    login(request, user)
                    request.session['role'] = role_type
                    if role_type == 'candidate':
                        return redirect('candidate_dashboard')
                    else:
                        return redirect('recruitpanel:add_company')
        else:
            if not raw_phone or not pin:
                error = 'Phone number and PIN are required.'
            else:
                user = authenticate(request, phone=phone_with_code, pin=pin)
                if user is None:
                    user = authenticate(request, phone=raw_phone, pin=pin)
                if user is None:
                    if UserAuth.objects.filter(phone=phone_with_code).exists() or UserAuth.objects.filter(phone=raw_phone).exists():
                        error = 'Invalid PIN.'
                    else:
                        error = 'Phone number not found. Please register.'

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
            website=request.POST.get('website', '').strip(),
            email=request.POST.get('email', '').strip(),
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
    candidate = _get_candidate(request.user)
    return render(request, 'frontend/portal/candidate_dashboard.html', {'candidate': candidate})


def candidate_logout(request, company_slug=None):
    logout(request)
    return redirect('landing')


def candidate_register(request, company_slug=None):
    if request.user.is_authenticated:
        if request.user.roles.filter(role='candidate', is_active=True).exists():
            return redirect('candidate_dashboard')
        logout(request)

    error = None
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        phone = request.POST.get('phone', '').strip()
        pin = request.POST.get('pin', '').strip()

        if not name or not phone or not pin:
            error = 'All fields are required.'
        elif UserAuth.objects.filter(phone=phone).exists():
            error = 'This phone number is already registered. Please sign in.'
        else:
            username = phone
            base_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f'{base_username}-{counter}'
                counter += 1

            secretname = re.sub(r'[^a-z0-9]', '', name.lower())[:20] or f'user{phone[-4:]}'
            user = User.objects.create_user(username=username)
            user_auth = UserAuth.objects.create(user=user, phone=phone, secretname=secretname)
            user_auth.set_pin(pin)
            user_auth.save()

            UserRole.objects.create(
                user=user,
                role='candidate',
                is_active=True,
            )

            Candidate.objects.create(
                user=user,
                full_name=name,
                email=user_auth.secretname,
                phone=phone,
            )

            user = authenticate(request, phone=phone, pin=pin)
            if user:
                login(request, user)
                request.session['role'] = 'candidate'
                return redirect('candidate_dashboard')

    return render(request, 'frontend/portal/candidate_register.html', {'error': error})


def _get_candidate(user):
    candidate, _ = Candidate.objects.get_or_create(
        user=user,
        defaults={
            'full_name': user.get_full_name() or user.username,
            'email': getattr(getattr(user, 'auth', None), 'secretname', user.username),
            'phone': getattr(getattr(user, 'auth', None), 'phone', ''),
        },
    )
    return candidate


@candidate_required
def candidate_profile(request, company_slug=None):
    candidate = _get_candidate(request.user)
    return render(request, 'frontend/portal/candidate_profile.html', {'candidate': candidate})


@candidate_required
def candidate_edit_profile(request, company_slug=None):
    candidate = _get_candidate(request.user)
    return render(request, 'frontend/portal/candidate_edit_profile.html', {'candidate': candidate})


@candidate_required
def candidate_jobs(request, company_slug=None):
    return render(request, 'frontend/portal/candidate_jobs.html')


@candidate_required
def upload_resume(request, company_slug=None):
    if request.method != 'POST':
        return redirect('candidate_profile')

    candidate = _get_candidate(request.user)

    if 'resume' not in request.FILES:
        messages.error(request, 'No file selected.')
        return redirect('candidate_profile')

    resume_file = request.FILES['resume']
    ext = Path(resume_file.name).suffix.lower()
    if ext not in ('.pdf', '.docx', '.txt'):
        messages.error(request, 'Only PDF, DOCX, and TXT files are accepted.')
        return redirect('candidate_profile')

    candidate.resume.save(resume_file.name, resume_file)

    try:
        from agents.extractor import process_cv
        result = process_cv(candidate.resume.path)
        if not result.get('raw_text') or result['raw_text'] == '[No text extracted]':
            messages.error(request, 'Could not extract text from the file.')
            return redirect('candidate_profile')

        candidate.raw_text = result.get('raw_text', '')
        candidate.summary = result.get('summary', '')
        candidate.experience = result.get('experience', [])
        candidate.education = result.get('education', [])
        candidate.certifications = result.get('certifications', [])
        candidate.languages = result.get('languages', [])
        candidate.contact = result.get('contact', {})
        candidate.total_experience_years = result.get('total_experience_years')

        for skill_data in result.get('skills', []):
            name = skill_data.get('name', '').strip()
            level = skill_data.get('level', '')
            if name:
                skill, _ = Skill.objects.get_or_create(name=name, defaults={'category': 'Unknown'})
                CandidateSkill.objects.get_or_create(candidate=candidate, skill=skill, defaults={'level': level or ''})

        candidate.save()
        messages.success(request, 'Resume uploaded and skills extracted successfully!')
    except Exception as e:
        candidate.save()
        messages.error(request, f'Extraction failed: {str(e)}')

    return redirect('candidate_profile')


@candidate_required
def candidate_applications(request, company_slug=None):
    candidate = _get_candidate(request.user)
    applications = Application.objects.filter(candidate=candidate).order_by('-submitted_at')
    return render(request, 'frontend/portal/candidate_applications.html', {
        'candidate': candidate,
        'applications': applications,
    })


@csrf_exempt
@candidate_required
def api_candidate_profile(request, company_slug=None):
    candidate = _get_candidate(request.user)
    if request.method == 'PUT':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON'}, status=400)

        if 'full_name' in data:
            candidate.full_name = data['full_name']
        if 'email' in data:
            candidate.email = data['email']
        if 'phone' in data:
            candidate.phone = data['phone']
        if 'summary' in data:
            candidate.summary = data['summary']
        if 'experience' in data:
            candidate.experience = data['experience']
        if 'education' in data:
            candidate.education = data['education']
        if 'certifications' in data:
            candidate.certifications = data['certifications']
        if 'languages' in data:
            candidate.languages = data['languages']
        if 'contact' in data:
            candidate.contact = data['contact']
        if 'total_experience_years' in data:
            candidate.total_experience_years = data['total_experience_years']

        if 'skills' in data:
            candidate.candidate_skills.all().delete()
            seen = set()
            for sd in data['skills']:
                name = sd.get('name', '').strip()
                if name and name.lower() not in seen:
                    seen.add(name.lower())
                    skill, _ = Skill.objects.get_or_create(name=name, defaults={'category': 'Unknown'})
                    CandidateSkill.objects.get_or_create(candidate=candidate, skill=skill, defaults={'level': sd.get('level', '')})

        candidate.save()
        return JsonResponse({'success': True})

    return JsonResponse({
        'id': candidate.id,
        'full_name': candidate.full_name,
        'email': candidate.email,
        'phone': candidate.phone,
        'summary': candidate.summary,
        'experience': candidate.experience,
        'education': candidate.education,
        'certifications': candidate.certifications,
        'languages': candidate.languages,
        'contact': candidate.contact,
        'total_experience_years': candidate.total_experience_years,
        'skills': [
            {'name': cs.skill.name, 'level': cs.level}
            for cs in candidate.candidate_skills.select_related('skill').all()
        ],
    })


def api_skills(request, company_slug=None):
    query = request.GET.get('q', '').strip()
    skills = Skill.objects.all()
    if query:
        skills = skills.filter(name__icontains=query)
    return JsonResponse(list(skills.values('id', 'name', 'category')), safe=False)


def api_jobs_search(request, company_slug=None):
    skills_param = request.GET.get('skills', '').strip()
    jobs = JobPosition.objects.filter(is_active=True).select_related('company').prefetch_related('skills')

    if skills_param:
        skill_names = [s.strip() for s in skills_param.split(',') if s.strip()]
        if skill_names:
            jobs = jobs.filter(skills__name__in=skill_names).distinct()

    results = []
    for job in jobs:
        job_skills = list(job.skills.values_list('name', flat=True))
        match_count = 0
        if skills_param:
            match_count = sum(1 for s in job_skills if s.lower() in [x.lower() for x in skill_names])
        results.append({
            'id': job.id,
            'title': job.title,
            'company': job.company.name,
            'company_slug': job.company.slug,
            'location': job.location,
            'description': job.description[:300] if job.description else '',
            'requirements': job.requirements[:300] if job.requirements else '',
            'skills': job_skills,
            'match_count': match_count,
            'total_skills': len(job_skills),
        })

    if skills_param:
        results.sort(key=lambda j: j['match_count'], reverse=True)

    return JsonResponse(results, safe=False)


@candidate_required
def api_apply_job(request, company_slug=None):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=405)

    try:
        data = json.loads(request.body)
    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    job_id = data.get('job_id')
    if not job_id:
        return JsonResponse({'error': 'job_id required'}, status=400)

    job = get_object_or_404(JobPosition, id=job_id, is_active=True)
    candidate = _get_candidate(request.user)

    if Application.objects.filter(candidate=candidate, position=job.title, company=job.company).exists():
        return JsonResponse({'error': 'You have already applied for this position.'}, status=409)

    application = Application.objects.create(
        company=job.company,
        candidate=candidate,
        full_name=candidate.full_name,
        email=candidate.email,
        phone=candidate.phone,
        position=job.title,
        experience=int(candidate.total_experience_years or 0),
        cover_letter='Applied via candidate portal.',
    )

    if candidate.resume:
        try:
            from shutil import copy2
            src = candidate.resume.path
            ext = Path(src).suffix
            dest_name = f'app_{application.id}_resume{ext}'
            application.resume.save(dest_name, candidate.resume.file)
        except Exception:
            pass

    if candidate.summary and job.description:
        try:
            from agents.extractor import extract_with_ai
            prompt = f"""Based on this candidate profile and job description, generate a tailored resume summary (2-3 sentences) and a professional cover letter (3-4 paragraphs).

Candidate Profile:
{candidate.summary}

Skills: {', '.join(cs.skill.name for cs in candidate.candidate_skills.select_related('skill').all())}

Experience: {json.dumps(candidate.experience)}

Job Title: {job.title}
Job Description: {job.description}
Requirements: {job.requirements}

Return JSON with keys: "tailored_resume" and "cover_letter"."""
            result = extract_with_ai(prompt)
            if result:
                application.tailored_resume = result.get('tailored_resume', '') or result.get('cover_letter', '')
                application.generated_cover_letter = result.get('cover_letter', '') or result.get('tailored_resume', '')
                application.save()
        except Exception:
            pass

    return JsonResponse({'success': True, 'application_id': application.id})
