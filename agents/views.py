from pathlib import Path
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.conf import settings
from api.models import Application
from agents.models import CVExtract
from agents.extractor import process_cv


@csrf_exempt
@require_POST
def extract_cv(request):
    application_id = request.POST.get('application_id')
    resume_file = request.FILES.get('resume')

    if not application_id and not resume_file:
        return JsonResponse({'error': 'Provide application_id or a resume file'}, status=400)

    application = None
    file_path = None

    if application_id:
        try:
            application = Application.objects.get(id=application_id)
        except Application.DoesNotExist:
            return JsonResponse({'error': f'Application {application_id} not found'}, status=404)

        if not application.resume:
            return JsonResponse({'error': f'Application {application_id} has no resume file'}, status=400)

        file_path = Path(settings.MEDIA_ROOT) / application.resume.name
        if not file_path.exists():
            return JsonResponse({'error': f'Resume file not found on disk: {file_path}'}, status=400)

    elif resume_file:
        file_path = Path(settings.MEDIA_ROOT) / 'resumes' / resume_file.name
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, 'wb+') as f:
            for chunk in resume_file.chunks():
                f.write(chunk)

        full_name = request.POST.get('full_name', resume_file.name)
        application = Application.objects.create(
            full_name=full_name,
            email=request.POST.get('email', ''),
            phone=request.POST.get('phone', ''),
            position=request.POST.get('position', ''),
            experience=int(request.POST.get('experience', 0)),
            resume=resume_file,
        )

    data = process_cv(file_path)
    if not data['raw_text'].strip() or data['raw_text'] == '[No text extracted]':
        return JsonResponse({'error': 'Could not extract text from file', 'raw_text': data['raw_text']}, status=422)

    extract = CVExtract.objects.create(
        application=application,
        raw_text=data['raw_text'],
        summary=data['summary'],
        skills=data['skills'],
        experience=data['experience'],
        education=data['education'],
        certifications=data['certifications'],
        languages=data.get('languages', []),
        contact=data.get('contact', {}),
        total_experience_years=data.get('total_experience_years'),
        status='completed',
    )

    return JsonResponse({
        'id': extract.id,
        'application_id': application.id,
        'candidate_name': application.full_name,
        'summary': data['summary'],
        'skills': data['skills'],
        'experience': data['experience'],
        'education': data['education'],
        'certifications': data['certifications'],
        'languages': data.get('languages', []),
        'contact': data.get('contact', {}),
        'total_experience_years': data.get('total_experience_years'),
        'extracted_at': extract.extracted_at.isoformat(),
    })
