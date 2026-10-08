"""
Lightweight, offline rule-based AI helpers (PRINTPROX: AI Recommendations + Chatbot).

No external API, no cost. `recommend()` ranks catalog products by category overlap
and popularity against the customer's browse/purchase history; `chatbot_reply()` is a
small intent/FAQ engine over the CMS FAQ table plus order-tracking shortcuts.
"""
from django.db.models import Count


def recommend(request, limit=8, exclude_ids=None):
    """Personalised product picks.

    Strategy (in order): products in categories the user recently viewed/bought,
    then best-sellers, then newest — de-duplicated. Pure DB queries.
    """
    from products.models import Product

    exclude_ids = set(exclude_ids or [])
    viewed = request.session.get("recently_viewed", [])
    picks, seen = [], set(exclude_ids)

    cat_ids = list(
        Product.objects.filter(id__in=viewed).values_list("category_id", flat=True)
    )
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        cat_ids += list(
            Product.objects.filter(orderitem__order__user=user)
            .values_list("category_id", flat=True)
        )

    def _add(qs):
        for p in qs:
            if p.id not in seen:
                picks.append(p)
                seen.add(p.id)

    base = Product.objects.filter(active=True)
    if cat_ids:
        _add(base.filter(category_id__in=cat_ids).order_by("-sold_count")[: limit * 2])
    _add(base.order_by("-sold_count")[: limit * 2])
    _add(base.order_by("-created_at")[: limit * 2])
    return picks[:limit]


def track_view(request, product_id):
    """Remember the last viewed products in the session (drives recommend())."""
    viewed = request.session.get("recently_viewed", [])
    viewed = [pid for pid in viewed if pid != product_id]
    viewed.insert(0, product_id)
    request.session["recently_viewed"] = viewed[:20]
    request.session.modified = True


# --- Chatbot --------------------------------------------------------------
_INTENTS = [
    (("track", "where is my order", "order status", "tracking"),
     "You can track any order from your <a href='/accounts/orders/'>Orders page</a> "
     "or the <a href='/track/'>Track Order</a> page using your order number."),
    (("delivery", "shipping", "how long", "dispatch"),
     "We deliver PAN-India in {delivery}. Orders above ₹{free} ship free."),
    (("bulk", "corporate", "quotation", "quote", "wholesale"),
     "For bulk & corporate gifting, please <a href='/quotations/'>request a quotation</a> "
     "and our team will share a custom proposal."),
    (("payment", "razorpay", "upi", "pay"),
     "We accept UPI, cards and net-banking via Razorpay at checkout. GST invoices are provided."),
    (("customi", "logo", "print", "design"),
     "Most products are customisable — open a product and click <b>Customize</b> to add your "
     "logo/text and preview the print."),
    (("return", "refund", "cancel"),
     "Reach our support team for returns/refunds. Personalised items are made-to-order."),
    (("contact", "support", "help", "phone", "email"),
     "Reach us at {email} or via WhatsApp. We're happy to help!"),
]


def chatbot_reply(text):
    from django.conf import settings
    from cms.models import FAQ

    t = (text or "").lower().strip()
    rules = settings.TEEPRESSO
    fmt = {"delivery": rules["DELIVERY_DAYS"], "free": rules["FREE_SHIP_OVER"],
           "email": rules["SUPPORT_EMAIL"]}

    if not t:
        return "Hi! I'm Teebot 🤖 — ask me about products, delivery, bulk orders, or tracking."

    for keys, reply in _INTENTS:
        if any(k in t for k in keys):
            return reply.format(**fmt)

    # fall back to the FAQ knowledge base
    for faq in FAQ.objects.filter(active=True):
        words = [w for w in faq.question.lower().split() if len(w) > 3]
        if any(w in t for w in words):
            return faq.answer

    return ("I'm not sure about that yet — please "
            f"<a href='/contact/'>contact our team</a> or email {rules['SUPPORT_EMAIL']}.")
