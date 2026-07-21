from django.db import models
from django.conf import settings


class Company(models.Model):
    name = models.CharField('Company Name', max_length=200)
    slug = models.SlugField('Slug', max_length=100, unique=True, help_text='Used in URL: /slug/...')
    brand_color = models.CharField('Brand Color', max_length=7, default='#f59e0b', help_text='Hex color for branding')
    logo_url = models.URLField('Logo URL', blank=True)
    logo = models.ImageField('Logo', upload_to='company_logos/', blank=True)
    website = models.URLField('Website', blank=True, help_text='Company website (e.g. https://acme.com)')
    email = models.EmailField('Company Email', blank=True, help_text='Email address matching the website domain')
    address = models.TextField('Address', blank=True, help_text='Street, city, state, zip')
    summary = models.TextField('Summary', blank=True, help_text='Brief description of the company')
    is_active = models.BooleanField('Active', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Company'
        verbose_name_plural = 'Companies'

    def __str__(self):
        return self.name


class CompanyEditRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='edit_requests')
    requested_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='company_edit_requests')
    name = models.CharField('Company Name', max_length=200, blank=True)
    website = models.URLField('Website', blank=True)
    email = models.EmailField('Company Email', blank=True)
    address = models.TextField('Address', blank=True)
    summary = models.TextField('Summary', blank=True)
    brand_color = models.CharField('Brand Color', max_length=7, blank=True)
    logo = models.ImageField('Logo', upload_to='company_edit_logos/', blank=True, null=True)
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='reviewed_edit_requests',
    )
    reviewed_at = models.DateTimeField('Reviewed At', null=True, blank=True)
    created_at = models.DateTimeField('Submitted', auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Company Edit Request'
        verbose_name_plural = 'Company Edit Requests'

    def __str__(self):
        return f'Edit request for {self.company.name} by {self.requested_by.username}'
