from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from company.models import Company
from api.models import UserRole


User = get_user_model()


class AddCompanyTests(TestCase):
    def test_recruiter_can_add_second_company(self):
        user = User.objects.create_user(username='recruiter-1')
        first_company = Company.objects.create(name='First Co', slug='first-co')
        UserRole.objects.create(
            user=user,
            role='recruiter',
            company=first_company,
            sub_role='admin',
            is_active=True,
        )

        self.client.force_login(user)

        response = self.client.post(
            reverse('recruitpanel:add_company'),
            {
                'name': 'Second Co',
                'website': 'https://secondco.example',
                'email': 'hello@secondco.example',
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, reverse('recruitpanel:recruitpanel_dashboard'))
        self.assertTrue(Company.objects.filter(name='Second Co').exists())
        self.assertEqual(
            UserRole.objects.filter(user=user, role='recruiter', is_active=True).count(),
            2,
        )
