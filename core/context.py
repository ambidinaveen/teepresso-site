from django.conf import settings


def site_context(request):
    """Brand info, nav categories (mega menu), cart/wishlist badges — every page."""
    from products.models import Category
    from cart.utils import get_cart

    cart = get_cart(request, create=False)
    wishlist_count = 0
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        wishlist_count = user.wishlist_items.count()

    return {
        "BRAND": settings.TEEPRESSO["BRAND"],
        "RULES": settings.TEEPRESSO,
        "INTEGRATIONS": settings.INTEGRATIONS,
        "nav_categories": Category.objects.filter(active=True, parent__isnull=True)
        .prefetch_related("children")
        .order_by("sort", "name"),
        "cart_count": cart.item_count if cart else 0,
        "wishlist_count": wishlist_count,
        "support_wa": _wa_link(settings.TEEPRESSO["SUPPORT_PHONE"]),
    }


def _wa_link(phone, text="Hi Teepresso, I have a question."):
    digits = "".join(c for c in phone if c.isdigit())
    from urllib.parse import quote
    return f"https://wa.me/{digits}?text={quote(text)}"
