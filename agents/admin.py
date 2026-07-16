from django.contrib import admin
from .models import CVExtract


class CVExtractAdmin(admin.ModelAdmin):
    list_display = ['application', 'total_experience_years', 'status', 'extracted_at']
    list_filter = ['status']
    search_fields = ['application__full_name', 'application__email']
    readonly_fields = ['raw_text', 'extracted_at']


admin.site.register(CVExtract, CVExtractAdmin)
