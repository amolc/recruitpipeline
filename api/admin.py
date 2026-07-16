from django.contrib import admin
from .models import Application, JobPosition, Automation, Company, Stage, UserProfile


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'is_active', 'created_at')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'slug')


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'company', 'role')
    list_filter = ('company', 'role')
    search_fields = ('user__username', 'company__name')


@admin.register(Stage)
class StageAdmin(admin.ModelAdmin):
    list_display = ('company', 'key', 'label', 'order')
    list_filter = ('company',)
    search_fields = ('label',)


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'company', 'email', 'position', 'experience', 'status', 'submitted_at')
    list_filter = ('company', 'position', 'status', 'submitted_at')
    search_fields = ('full_name', 'email', 'position')


@admin.register(JobPosition)
class JobPositionAdmin(admin.ModelAdmin):
    list_display = ('title', 'company', 'base_salary', 'hourly_rate', 'location', 'is_active')
    list_filter = ('company', 'is_active', 'location')
    search_fields = ('title', 'location')


@admin.register(Automation)
class AutomationAdmin(admin.ModelAdmin):
    list_display = ('position', 'company', 'stage', 'description')
    list_filter = ('company', 'position', 'stage')
    search_fields = ('description',)
