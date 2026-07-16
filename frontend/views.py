from django.shortcuts import render, get_object_or_404
from django.http import Http404
from api.models import Company, JobPosition


def landing(request):
    companies = Company.objects.filter(is_active=True)
    return render(request, 'frontend/landing.html', {'companies': companies})


def apply(request, company_slug=None):
    if not request.company:
        raise Http404('Company not found')
    positions = JobPosition.objects.filter(company=request.company, is_active=True)
    return render(request, 'frontend/apply.html', {
        'company': request.company,
        'positions': positions,
    })
