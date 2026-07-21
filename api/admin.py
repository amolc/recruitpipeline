from django.contrib import admin
from .models import Application, JobPosition, Automation, Stage, UserProfile, Skill, Candidate, CandidateSkill


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


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ('name', 'category')
    list_filter = ('category',)
    search_fields = ('name',)


@admin.register(Candidate)
class CandidateAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'phone', 'total_experience_years', 'created_at')
    search_fields = ('full_name', 'email', 'phone')


@admin.register(CandidateSkill)
class CandidateSkillAdmin(admin.ModelAdmin):
    list_display = ('candidate', 'skill', 'level')
    list_filter = ('level',)
