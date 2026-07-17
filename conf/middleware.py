from django.http import Http404
from api.models import Company, UserRole


EXCLUDED_PREFIXES = ('admin', 'super', 'superadmin', 'panel', 'candidate', 'api', 'static', 'media', 'register', 'recruitpanel', 'choose-role', 'login')


class CompanyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.company = None
        parts = request.path_info.strip('/').split('/')
        if parts and parts[0] and parts[0] not in EXCLUDED_PREFIXES:
            try:
                request.company = Company.objects.get(slug=parts[0])
            except Company.DoesNotExist:
                pass
        # Fallback: set company from session if available
        if not request.company and request.session.get('company_id'):
            try:
                request.company = Company.objects.get(pk=request.session['company_id'])
            except Company.DoesNotExist:
                pass

        # Expose companies the current user is a recruiter for (used in recruitpanel header)
        request.user_companies = []
        if request.user.is_authenticated:
            request.user_companies = list(Company.objects.filter(
                userrole__user=request.user,
                userrole__role='recruiter',
                userrole__is_active=True,
            ).distinct())

        return self.get_response(request)
