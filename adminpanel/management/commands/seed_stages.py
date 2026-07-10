from django.core.management.base import BaseCommand
from api.models import Stage, STAGES


class Command(BaseCommand):
    help = 'Seeds default pipeline stages from STAGES constant'

    def handle(self, *args, **options):
        created = 0
        for order, (key, label) in enumerate(STAGES):
            _, is_new = Stage.objects.get_or_create(
                key=key,
                defaults={'label': label, 'order': order}
            )
            if is_new:
                created += 1
            else:
                Stage.objects.filter(key=key).update(label=label, order=order)
        self.stdout.write(self.style.SUCCESS(f'Seeded {created} stage(s) ({len(STAGES)} total)'))
