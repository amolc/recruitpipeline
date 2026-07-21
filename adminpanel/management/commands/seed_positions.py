from django.core.management.base import BaseCommand, CommandError
from company.models import Company
from api.models import JobPosition

POSITIONS = [
    'Solar Panel Fabricator',
    'Solar Electrician',
    'Site Supervisor',
    'Solar Installer',
    'Roofer / Mounting Specialist',
    'Electrical Engineer (Solar)',
    'Commissioning Technician',
    'Quality Inspector',
]

class Command(BaseCommand):
    help = 'Seeds job positions for a company'

    def add_arguments(self, parser):
        parser.add_argument('--company', type=str, required=True, help='Company slug')

    def handle(self, *args, **options):
        slug = options['company']
        try:
            company = Company.objects.get(slug=slug)
        except Company.DoesNotExist:
            raise CommandError(f'Company with slug "{slug}" not found')

        created = 0
        for title in POSITIONS:
            _, is_new = JobPosition.objects.get_or_create(
                company=company,
                title=title,
                defaults={'company': company},
            )
            if is_new:
                created += 1
        self.stdout.write(self.style.SUCCESS(
            f'Seeded {created} position(s) for "{company.name}" ({len(POSITIONS)} total)'
        ))
