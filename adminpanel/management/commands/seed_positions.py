from django.core.management.base import BaseCommand
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
    help = 'Seeds job positions from the frontend form'

    def handle(self, *args, **options):
        created = 0
        for title in POSITIONS:
            _, is_new = JobPosition.objects.get_or_create(title=title)
            if is_new:
                created += 1
        self.stdout.write(self.style.SUCCESS(f'Seeded {created} position(s) ({len(POSITIONS)} total)'))
