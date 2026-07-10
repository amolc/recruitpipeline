from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates the default admin user if it does not exist'

    def handle(self, *args, **options):
        if not User.objects.filter(username='admin').exists():
            User.objects.create_superuser('admin', 'admin@solarsolutions.com', 'admin123')
            self.stdout.write(self.style.SUCCESS('Default admin created (admin / admin123)'))
        else:
            self.stdout.write(self.style.WARNING('Default admin already exists'))
