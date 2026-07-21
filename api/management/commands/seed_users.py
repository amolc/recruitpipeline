from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from company.models import Company
from api.models import UserAuth, UserRole

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates test users for the three portals'

    def handle(self, *args, **options):
        company, _ = Company.objects.get_or_create(
            slug='demo',
            defaults={'name': 'Demo Company', 'brand_color': '#059669'}
        )

        users_data = [
            {
                'username': 'superadmin',
                'phone': '1111111111',
                'pin': '1111',
                'secretname': 'admin',
                'role': 'superadmin',
            },
            {
                'username': 'recruiter',
                'phone': '2222222222',
                'pin': '2222',
                'secretname': 'recruit',
                'role': 'recruiter',
                'company': company,
            },
            {
                'username': 'candidate',
                'phone': '3333333333',
                'pin': '3333',
                'secretname': 'candid',
                'role': 'candidate',
            },
        ]

        for data in users_data:
            role = data.pop('role')
            company = data.pop('company', None)
            phone = data.pop('phone')
            pin = data.pop('pin')
            secretname = data.pop('secretname')
            username = data.pop('username')

            user, created = User.objects.get_or_create(
                username=username,
                defaults={**data},
            )
            if created:
                user.set_password(pin)
                user.save()

            user_auth, auth_created = UserAuth.objects.get_or_create(
                user=user,
                defaults={'phone': phone, 'secretname': secretname},
            )
            if auth_created:
                user_auth.set_pin(pin)
                user_auth.save()

            role_obj, role_created = UserRole.objects.get_or_create(
                user=user,
                role=role,
                defaults={'company': company, 'sub_role': 'admin' if role == 'recruiter' else None},
            )

            status = 'created' if created else 'already exists'
            self.stdout.write(f'  {username} ({role}) — {status}')

        self.stdout.write(self.style.SUCCESS('Seed complete'))
