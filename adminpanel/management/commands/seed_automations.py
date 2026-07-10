from django.core.management.base import BaseCommand
from api.models import JobPosition, Automation, DEFAULT_AUTOMATIONS

class Command(BaseCommand):
    help = 'Seeds default automations for all positions'

    def handle(self, *args, **options):
        created = 0
        for pos in JobPosition.objects.all():
            for stage, desc in DEFAULT_AUTOMATIONS.items():
                _, is_new = Automation.objects.get_or_create(
                    position=pos, stage=stage,
                    defaults={'description': desc}
                )
                if is_new:
                    created += 1
        self.stdout.write(self.style.SUCCESS(f'Seeded {created} automation(s)'))
