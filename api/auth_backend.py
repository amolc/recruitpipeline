from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model

User = get_user_model()


class PhoneAuthBackend(BaseBackend):
    def authenticate(self, request, phone=None, pin=None):
        if not phone or not pin:
            return None
        try:
            from api.models import UserAuth
            user_auth = UserAuth.objects.select_related('user').get(phone=phone)
            if user_auth.check_pin(pin) and user_auth.user.is_active:
                return user_auth.user
        except UserAuth.DoesNotExist:
            return None
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
