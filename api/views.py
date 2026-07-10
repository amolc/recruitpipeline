from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_GET
from django.http import JsonResponse
from .models import Application, JobPosition, Stage

@csrf_exempt
@require_POST
def submit_application(request):
    try:
        app = Application.objects.create(
            full_name=request.POST.get('fullName', '').strip(),
            email=request.POST.get('email', '').strip(),
            phone=request.POST.get('phone', '').strip(),
            position=request.POST.get('position', '').strip(),
            experience=int(request.POST.get('experience', 0)),
            resume=request.FILES.get('resume'),
            cover_letter=request.POST.get('coverLetter', '').strip(),
        )
        return JsonResponse({'success': True, 'id': app.id})
    except (ValueError, TypeError) as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@csrf_exempt
@require_POST
def update_status(request, application_id):
    try:
        app = Application.objects.get(id=application_id)
        new_status = request.POST.get('status', '')
        valid_keys = list(Stage.objects.values_list('key', flat=True))
        if new_status in valid_keys:
            app.status = new_status
            app.save()
            return JsonResponse({'success': True, 'status': new_status})
        return JsonResponse({'success': False, 'error': 'Invalid status'}, status=400)
    except Application.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Not found'}, status=404)

@require_GET
def list_positions(request):
    positions = JobPosition.objects.filter(is_active=True).values('id', 'title')
    return JsonResponse(list(positions), safe=False)
