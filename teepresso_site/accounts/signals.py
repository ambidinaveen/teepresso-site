from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from cart.utils import merge_session_cart


@receiver(user_logged_in)
def _merge_cart_on_login(sender, request, user, **kwargs):
    """Carry an anonymous session cart into the user's cart after login."""
    try:
        merge_session_cart(request, user)
    except Exception:
        pass
