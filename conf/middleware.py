from django.http import Http404
from api.models import Company


class CompanyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.company = None
        parts = request.path_info.strip('/').split('/')
        if parts and parts[0] and parts[0] not in ('admin', 'super', 'static', 'media'):
            try:
                request.company = Company.objects.get(slug=parts[0])
            except Company.DoesNotExist:
                pass
        return self.get_response(request)
