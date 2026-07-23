from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth import get_user_model
from company.models import Company

User = get_user_model()


class Skill(models.Model):
    name = models.CharField(max_length=200, unique=True)
    category = models.CharField(max_length=50, blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'Skill'
        verbose_name_plural = 'Skills'

    def __str__(self):
        return self.name


class Candidate(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='candidate_profile')
    full_name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    phone = models.CharField(max_length=30, blank=True)
    resume = models.FileField(upload_to='candidate_resumes/', blank=True, null=True)
    raw_text = models.TextField(blank=True)
    summary = models.TextField(blank=True)
    experience = models.JSONField(default=list, blank=True)
    education = models.JSONField(default=list, blank=True)
    certifications = models.JSONField(default=list, blank=True)
    languages = models.JSONField(default=list, blank=True)
    contact = models.JSONField(default=dict, blank=True)
    total_experience_years = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Candidate'
        verbose_name_plural = 'Candidates'

    def __str__(self):
        return self.full_name


class CandidateSkill(models.Model):
    LEVEL_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ]
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='candidate_skills')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name='candidate_skills')
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, blank=True)

    class Meta:
        unique_together = ('candidate', 'skill')
        verbose_name = 'Candidate Skill'
        verbose_name_plural = 'Candidate Skills'

    def __str__(self):
        return f'{self.candidate.full_name} — {self.skill.name}'


STAGES = [
    ('new', 'New'),
    ('screening', 'Screening'),
    ('shortlisted', 'Shortlisted'),
    ('interview', 'Interview'),
    ('offer', 'Offer'),
    ('hired', 'Hired'),
    ('rejected', 'Rejected'),
]

STAGE_KEYS = [s[0] for s in STAGES]


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('recruiter', 'Recruiter'),
        ('hiring_manager', 'Hiring Manager'),
    ]
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='members')
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='recruiter')

    class Meta:
        verbose_name = 'User Profile'

    def __str__(self):
        return f'{self.user.username} @ {self.company.name}'


class UserAuth(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='auth')
    phone = models.CharField('Phone Number', max_length=15, unique=True)
    pin = models.CharField('PIN', max_length=128)
    secretname = models.CharField('Secret Name', max_length=100)

    def set_pin(self, raw_pin):
        self.pin = make_password(raw_pin)

    def check_pin(self, raw_pin):
        return check_password(raw_pin, self.pin)

    def __str__(self):
        return self.phone

    class Meta:
        verbose_name = 'User Auth'
        verbose_name_plural = 'User Auths'


class UserRole(models.Model):
    ROLE_CHOICES = [
        ('superadmin', 'Super Admin'),
        ('recruiter', 'Recruiter'),
        ('candidate', 'Candidate'),
    ]
    SUB_ROLE_CHOICES = [
        ('admin', 'Admin'),
        ('recruiter', 'Recruiter'),
        ('hiring_manager', 'Hiring Manager'),
        ('viewer', 'Viewer'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='roles')
    role = models.CharField('Role', max_length=20, choices=ROLE_CHOICES)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, null=True, blank=True, related_name='user_roles')
    sub_role = models.CharField('Sub Role', max_length=20, choices=SUB_ROLE_CHOICES, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('user', 'role', 'company')
        verbose_name = 'User Role'
        verbose_name_plural = 'User Roles'

    def __str__(self):
        label = self.role
        if self.company:
            label += f' @ {self.company.name}'
        return label


class Stage(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='stages')
    key = models.CharField('Key', max_length=30)
    label = models.CharField('Label', max_length=100)
    order = models.IntegerField('Order', default=0)

    class Meta:
        ordering = ['order']
        unique_together = ('company', 'key')
        verbose_name = 'Pipeline Stage'
        verbose_name_plural = 'Pipeline Stages'

    def __str__(self):
        return self.label


class Application(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='applications')
    candidate = models.ForeignKey(Candidate, on_delete=models.SET_NULL, null=True, blank=True, related_name='applications')
    full_name = models.CharField('Full Name', max_length=200)
    email = models.EmailField('Email Address')
    phone = models.CharField('Phone Number', max_length=30)
    position = models.CharField('Position', max_length=200)
    experience = models.PositiveIntegerField('Years of Experience')
    resume = models.FileField('Resume / CV', upload_to='resumes/', blank=True, null=True)
    cover_letter = models.TextField('Why join us?')
    tailored_resume = models.TextField(blank=True)
    generated_cover_letter = models.TextField(blank=True)
    status = models.CharField('Status', max_length=30, default='new')
    submitted_at = models.DateTimeField('Submitted', auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']
        verbose_name = 'Application'
        verbose_name_plural = 'Applications'

    def __str__(self):
        return f'{self.full_name} — {self.position}'

    def status_label(self):
        try:
            return Stage.objects.get(key=self.status).label
        except Stage.DoesNotExist:
            return self.status


class JobPosition(models.Model):
    EMPLOYMENT_TYPES = [
        ('full_time', 'Full-time'),
        ('part_time', 'Part-time'),
        ('internship', 'Internship'),
        ('contract', 'Contract'),
    ]
    WORK_TYPES = [
        ('remote', 'Remote'),
        ('hybrid', 'Hybrid'),
        ('on_site', 'On-site'),
    ]
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='job_positions')
    title = models.CharField('Job Title', max_length=200)
    description = models.TextField('Job Description', blank=True)
    base_salary = models.DecimalField('Base Salary ($)', max_digits=10, decimal_places=2, null=True, blank=True)
    hourly_rate = models.DecimalField('Per Hour ($)', max_digits=8, decimal_places=2, null=True, blank=True)
    salary_max = models.DecimalField('Max Salary ($)', max_digits=10, decimal_places=2, null=True, blank=True)
    location = models.CharField('Location', max_length=200, blank=True)
    employment_type = models.CharField('Employment Type', max_length=20, choices=EMPLOYMENT_TYPES, default='full_time')
    work_type = models.CharField('Work Type', max_length=20, choices=WORK_TYPES, default='on_site')
    experience_required = models.PositiveIntegerField('Experience Required (years)', null=True, blank=True)
    requirements = models.TextField('Requirements', blank=True)
    skills = models.ManyToManyField(Skill, blank=True)
    is_active = models.BooleanField('Active', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['title']
        unique_together = ('company', 'title')
        verbose_name = 'Job Position'
        verbose_name_plural = 'Job Positions'

    def __str__(self):
        return f'{self.title} ({self.company.name})'

DEFAULT_AUTOMATIONS = {
    'new': '- Send acknowledgement email\n- Parse resume for skills/experience\n- Auto-tag by position match',
    'screening': '- Auto-screen with keyword matching\n- Run basic skills assessment\n- Schedule phone screen',
    'shortlisted': '- Send shortlist confirmation email\n- Notify hiring manager\n- Prepare interview packet',
    'interview': '- Auto-schedule via calendar\n- Send invite with prep materials\n- Send 24h reminder',
    'offer': '- Generate offer letter from template\n- Send offer details for approval\n- Track acceptance status',
    'hired': '- Trigger onboarding workflow\n- Send welcome packet\n- Create employee record in HRIS',
    'rejected': '- Send personalized rejection email\n- Add to future talent pool\n- Request interviewer feedback',
}

def seed_default_stages(company):
    for order, (key, label) in enumerate(STAGES):
        Stage.objects.get_or_create(
            company=company,
            key=key,
            defaults={'label': label, 'order': order},
        )


class Automation(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='automations')
    position = models.ForeignKey(JobPosition, on_delete=models.CASCADE, related_name='automations')
    stage = models.CharField('Stage', max_length=30)
    description = models.TextField('Description', blank=True)

    class Meta:
        unique_together = ('position', 'stage')
        verbose_name = 'Automation'
        verbose_name_plural = 'Automations'

    def __str__(self):
        return f'{self.position.title} / {self.stage}'


class Panelist(models.Model):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='panelists')
    name = models.CharField('Name', max_length=200)
    email = models.EmailField('Email', blank=True)
    phone = models.CharField('Phone', max_length=30, blank=True)
    specialization = models.TextField('Specialization', blank=True)
    is_active = models.BooleanField('Active', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Panelist'
        verbose_name_plural = 'Panelists'

    def __str__(self):
        return self.name


class Screening(models.Model):
    STATUS_CHOICES = [
        ('not_scheduled', 'Not Scheduled'),
        ('scheduled', 'Scheduled'),
        ('in_progress', 'In Progress'),
        ('passed', 'Passed'),
        ('failed', 'Failed'),
    ]
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='screenings')
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='screenings')
    position = models.ForeignKey(JobPosition, on_delete=models.CASCADE, related_name='screenings')
    screening_type = models.CharField('Screening Type', max_length=200, blank=True)
    panelist = models.ForeignKey(Panelist, on_delete=models.SET_NULL, null=True, blank=True, related_name='screenings')
    scheduled_at = models.DateTimeField('Scheduled At', null=True, blank=True)
    duration_minutes = models.PositiveIntegerField('Duration (min)', default=45)
    meeting_link = models.URLField('Meeting Link', max_length=500, blank=True)
    score = models.FloatField('Score', null=True, blank=True)
    status = models.CharField('Status', max_length=20, choices=STATUS_CHOICES, default='not_scheduled')
    notes = models.TextField('Notes', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-scheduled_at']
        verbose_name = 'Screening'
        verbose_name_plural = 'Screenings'

    def __str__(self):
        return f'{self.application.full_name} — {self.screening_type or self.position.title}'


@receiver(post_save, sender=Company)
def company_post_save(sender, instance, created, **kwargs):
    if created:
        seed_default_stages(instance)
