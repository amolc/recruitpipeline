from django.core.management.base import BaseCommand, CommandError
from api.models import Company, JobPosition, Automation, DEFAULT_AUTOMATIONS


class Command(BaseCommand):
    help = 'Seeds default automations for all positions of a company'

    def add_arguments(self, parser):
        parser.add_argument('--company', type=str, required=True, help='Company slug')

    def handle(self, *args, **options):
        slug = options['company']
        try:
            company = Company.objects.get(slug=slug)
        except Company.DoesNotExist:
            raise CommandError(f'Company with slug "{slug}" not found')

        created = 0
        for pos in JobPosition.objects.filter(company=company):
            for stage, desc in DEFAULT_AUTOMATIONS.items():
                _, is_new = Automation.objects.get_or_create(
                    company=company,
                    position=pos,
                    stage=stage,
                    defaults={'description': desc},
                )
                if is_new:
                    created += 1
        self.stdout.write(self.style.SUCCESS(
            f'Seeded {created} automation(s) for "{company.name}"'
        ))
