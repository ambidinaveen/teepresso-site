from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend
from django.db.models import Q


class EmailOrPhoneBackend(ModelBackend):
    """Authenticate with email OR phone OR username (PRINTPROX: email/mobile login)."""

    def authenticate(self, request, username=None, password=None, **kwargs):
        User = get_user_model()
        ident = username or kwargs.get("email")
        if not ident or not password:
            return None
        try:
            user = User.objects.get(
                Q(email__iexact=ident) | Q(phone=ident) | Q(username__iexact=ident)
            )
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            user = User.objects.filter(
                Q(email__iexact=ident) | Q(phone=ident) | Q(username__iexact=ident)
            ).first()
        if user and user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
