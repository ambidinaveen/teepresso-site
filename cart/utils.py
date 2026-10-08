from .models import Cart


def get_cart(request, create=True):
    """Return the active cart for this request (user cart or session cart)."""
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        if create:
            cart, _ = Cart.objects.get_or_create(user=user)
            return cart
        return Cart.objects.filter(user=user).first()

    key = request.session.session_key
    if not key:
        if not create:
            return None
        request.session.save()
        key = request.session.session_key
    if create:
        cart, _ = Cart.objects.get_or_create(session_key=key, user__isnull=True)
        return cart
    return Cart.objects.filter(session_key=key, user__isnull=True).first()


def merge_session_cart(request, user):
    """On login, fold the anonymous session cart into the user's cart."""
    key = request.session.session_key
    if not key:
        return
    anon = Cart.objects.filter(session_key=key, user__isnull=True).first()
    if not anon:
        return
    user_cart, _ = Cart.objects.get_or_create(user=user)
    for item in anon.items.all():
        existing = user_cart.items.filter(
            product=item.product, variant_label=item.variant_label, design=item.design
        ).first()
        if existing:
            existing.qty += item.qty
            existing.save(update_fields=["qty"])
        else:
            item.cart = user_cart
            item.save(update_fields=["cart"])
    if not user_cart.coupon and anon.coupon:
        user_cart.coupon = anon.coupon
        user_cart.save(update_fields=["coupon"])
    anon.delete()
