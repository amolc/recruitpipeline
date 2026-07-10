from django.contrib import admin
from .models import Application, JobPosition, Automation

@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'position', 'experience', 'status', 'submitted_at')
    list_filter = ('position', 'status', 'submitted_at')
    search_fields = ('full_name', 'email', 'position')
    readonly_fields = ('submitted_at',)

@admin.register(JobPosition)
class JobPositionAdmin(admin.ModelAdmin):
    list_display = ('title', 'base_salary', 'hourly_rate', 'location', 'is_active')
    list_filter = ('is_active', 'location')
    search_fields = ('title', 'location')

@admin.register(Automation)
class AutomationAdmin(admin.ModelAdmin):
    list_display = ('position', 'stage', 'description')
    list_filter = ('position', 'stage')
    search_fields = ('description',)
