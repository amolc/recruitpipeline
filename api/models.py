from django.db import models

STAGES = [
    ('new', 'New'),
    ('need_info', 'Need Info'),
    ('screening', 'Screening'),
    ('qualified', 'Qualified'),
    ('contacted', 'Contacted'),
    ('assessment', 'Assessment'),
    ('interview', 'Interview'),
    ('selected', 'Selected'),
    ('background_check', 'Background Check'),
    ('offer_sent', 'Offer Sent'),
    ('accepted', 'Accepted'),
    ('onboarded', 'Onboarded'),
    ('rejected', 'Rejected'),
]

STAGE_KEYS = [s[0] for s in STAGES]

class Stage(models.Model):
    key = models.CharField('Key', max_length=30, unique=True)
    label = models.CharField('Label', max_length=100)
    order = models.IntegerField('Order', default=0)

    class Meta:
        ordering = ['order']
        verbose_name = 'Pipeline Stage'
        verbose_name_plural = 'Pipeline Stages'

    def __str__(self):
        return self.label


class Application(models.Model):
    full_name = models.CharField('Full Name', max_length=200)
    email = models.EmailField('Email Address')
    phone = models.CharField('Phone Number', max_length=30)
    position = models.CharField('Position', max_length=200)
    experience = models.PositiveIntegerField('Years of Experience')
    resume = models.FileField('Resume / CV', upload_to='resumes/', blank=True, null=True)
    cover_letter = models.TextField('Why join us?')
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
    title = models.CharField('Job Title', max_length=200, unique=True)
    description = models.TextField('Job Description', blank=True)
    base_salary = models.DecimalField('Base Salary ($)', max_digits=10, decimal_places=2, null=True, blank=True)
    hourly_rate = models.DecimalField('Per Hour ($)', max_digits=8, decimal_places=2, null=True, blank=True)
    location = models.CharField('Location', max_length=200, blank=True)
    requirements = models.TextField('Requirements', blank=True)
    is_active = models.BooleanField('Active', default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['title']
        verbose_name = 'Job Position'
        verbose_name_plural = 'Job Positions'

    def __str__(self):
        return self.title

DEFAULT_AUTOMATIONS = {
    'new': '- Send acknowledgement email\n- Parse resume for skills/experience\n- Auto-tag by position match',
    'need_info': '- Detect incomplete application fields\n- Send follow-up email requesting missing documents\n- Flag for manual review',
    'screening': '- Auto-screen with keyword matching\n- Run basic skills assessment\n- Schedule phone screen',
    'qualified': '- Send qualification confirmation email\n- Add to talent pool\n- Notify hiring manager',
    'contacted': '- Track email open rates\n- Auto-follow-up after 3 days of no response\n- Log contact history',
    'assessment': '- Generate assessment link\n- Set deadline reminder\n- Auto-grade multiple-choice section',
    'interview': '- Auto-schedule via calendar\n- Send invite with prep materials\n- Send 24h reminder',
    'selected': '- Notify HR department\n- Initiate offer packet generation\n- Trigger background check request',
    'background_check': '- Send authorization form\n- Track check status via API\n- Flag results for review',
    'offer_sent': '- Generate offer letter from template\n- Send via DocuSign\n- Track signature status',
    'accepted': '- Trigger onboarding workflow\n- Send welcome packet\n- Create employee record in HRIS',
    'onboarded': '- Schedule orientation session\n- Assign equipment provisioning\n- Send 30-day survey',
    'rejected': '- Send personalized rejection email\n- Add to future talent pool\n- Request interviewer feedback',
}

class Automation(models.Model):
    position = models.ForeignKey(JobPosition, on_delete=models.CASCADE, related_name='automations')
    stage = models.CharField('Stage', max_length=30)
    description = models.TextField('Description', blank=True)

    class Meta:
        unique_together = ('position', 'stage')
        verbose_name = 'Automation'
        verbose_name_plural = 'Automations'

    def __str__(self):
        return f'{self.position.title} / {self.stage}'
