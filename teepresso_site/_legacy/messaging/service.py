"""
WhatsApp messaging service — SAFE BY DEFAULT.

- If the official WhatsApp Business API is configured (WHATSAPP_MODE=api + creds),
  messages are SENT AUTOMATICALLY.
- Otherwise the message is BUILT and QUEUED with a one-click wa.me link so staff
  send it manually. This has zero risk of a WhatsApp number ban, so it is safe to
  run on a live public server before you have the official API.

The single real-API swap-in point is `_send_via_api()`.
"""
import json
import logging
import urllib.request
from urllib.parse import quote_plus

from django.conf import settings
from django.urls import reverse

log = logging.getLogger(__name__)


def normalize_phone(phone):
    d = "".join(c for c in str(phone) if c.isdigit())
    if d and len(d) == 10:        # default India country code
        d = "91" + d
    return d


def wa_click_link(phone, text):
    return f"https://wa.me/{normalize_phone(phone)}?text={quote_plus(text)}"


def build_bill_text(order, bill_url):
    lines = [
        f"Hi {order.customer.name}, thank you for your order with Teepresso! 🎽",
        f"Order: {order.order_no}",
        f"Item: {order.design_summary}",
        f"Quantity: {order.qty_total} pcs",
        f"Total: ₹{order.total:,} (incl. {settings.TEEPRESSO['GST_RATE']}% GST)",
    ]
    if order.payment_status == order.Payment.PAID:
        lines.append("Payment: PAID ✅")
    else:
        lines.append("Payment: pending — please reply to confirm.")
    if bill_url:
        lines.append(f"View / download your bill: {bill_url}")
    lines.append(f"Delivery in {settings.TEEPRESSO['DELIVERY_DAYS']}.")
    return "\n".join(lines)


def api_configured():
    c = getattr(settings, "WHATSAPP", {})
    return bool(c.get("TOKEN") and c.get("PHONE_ID"))


def send_bill(order, request=None):
    """Create the bill message and either send it (API) or queue it (safe)."""
    from .models import WhatsAppMessage

    bill_path = reverse("storefront:bill", args=[order.order_no])
    bill_url = request.build_absolute_uri(bill_path) if request else bill_path
    text = build_bill_text(order, bill_url)

    msg = WhatsAppMessage(
        order=order,
        phone=normalize_phone(order.customer.phone),
        kind=WhatsAppMessage.Kind.BILL,
        body=text,
        link=bill_url,
        wa_link=wa_click_link(order.customer.phone, text),
    )

    if settings.INTEGRATIONS.get("WHATSAPP_MODE") == "api" and api_configured():
        try:
            _send_via_api(msg.phone, text)
            msg.status = WhatsAppMessage.Status.SENT
        except Exception as e:                      # never let a send break an order
            log.warning("WhatsApp API send failed for %s: %s", order.order_no, e)
            msg.status = WhatsAppMessage.Status.FAILED
            msg.error = str(e)
    else:
        msg.status = WhatsAppMessage.Status.QUEUED   # safe: one-click manual send

    msg.save()
    return msg


def _send_via_api(phone, text):
    """Real WhatsApp Business API (Meta Cloud) call. Runs ONLY when creds are set.
    Replace/extend here when you onboard a BSP. Consider moving to a Celery task."""
    c = settings.WHATSAPP
    url = f"https://graph.facebook.com/v20.0/{c['PHONE_ID']}/messages"
    payload = json.dumps({
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": text},
    }).encode()
    req = urllib.request.Request(
        url, data=payload,
        headers={"Authorization": f"Bearer {c['TOKEN']}", "Content-Type": "application/json"},
    )
    urllib.request.urlopen(req, timeout=10)
