from django.core.management.base import BaseCommand, CommandError
from company.models import Company
from api.models import Stage, STAGES


class Command(BaseCommand):
    help = 'Seeds default pipeline stages for a company'

    def add_arguments(self, parser):
        parser.add_argument('--company', type=str, required=True, help='Company slug')

    def handle(self, *args, **options):
        slug = options['company']
        try:
            company = Company.objects.get(slug=slug)
        except Company.DoesNotExist:
            raise CommandError(f'Company with slug "{slug}" not found')

        created = 0
        for order, (key, label) in enumerate(STAGES):
            _, is_new = Stage.objects.get_or_create(
                company=company,
                key=key,
                defaults={'label': label, 'order': order},
            )
            if is_new:
                created += 1
            else:
                Stage.objects.filter(company=company, key=key).update(label=label, order=order)
        self.stdout.write(self.style.SUCCESS(
            f'Seeded {created} stage(s) for "{company.name}" ({len(STAGES)} total)'
        ))
