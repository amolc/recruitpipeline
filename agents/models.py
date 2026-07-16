from django.db import models


class CVExtract(models.Model):
    application = models.ForeignKey('api.Application', on_delete=models.CASCADE, related_name='cv_extracts')
    raw_text = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    skills = models.JSONField(default=list, blank=True)
    experience = models.JSONField(default=list, blank=True)
    education = models.JSONField(default=list, blank=True)
    certifications = models.JSONField(default=list, blank=True)
    languages = models.JSONField(default=list, blank=True)
    contact = models.JSONField(default=dict, blank=True)
    total_experience_years = models.FloatField(null=True, blank=True)
    extracted_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, default='pending')

    class Meta:
        verbose_name = 'CV Extract'
        verbose_name_plural = 'CV Extracts'

    def __str__(self):
        name = self.application.full_name if self.application_id else '?'
        return f'CV Extract — {name}'
