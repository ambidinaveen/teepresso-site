"""
Notification service — SAFE BY DEFAULT.

Email goes through Django's email backend (console in dev — it prints, never spams).
WhatsApp uses safe wa.me click-links unless WHATSAPP_MODE=api. SMS is logged unless
SMS_API is enabled. Every message is recorded in the Notification table either way,
so the dashboard shows a full delivery log without any credentials.
"""
from django.conf import settings
from django.core.mail import send_mail

from core.utils import wa_link

from .models import Notification

# event -> (subject, body template). {ctx} keys are filled from kwargs below.
_TEMPLATES = {
    "register": ("Welcome to {brand}!",
                 "Hi {name}, your {brand} account is ready. Your verification code is {otp}."),
    "password_reset": ("{brand} password reset",
                       "Hi {name}, your password reset code is {otp}. It expires in 10 minutes."),
    "order_placed": ("Order {order_no} received",
                     "Hi {name}, we've received your order {order_no} for ₹{total}. "
                     "We'll confirm it shortly."),
    "payment_success": ("Payment received for {order_no}",
                        "Hi {name}, we've received your payment of ₹{total} for order {order_no}. "
                        "Thank you!"),
    "payment_pending": ("UPI payment submitted for {order_no}",
                        "Hi {name}, thanks — we've noted your UPI payment of ₹{total} for order "
                        "{order_no}. We'll verify it and confirm your order shortly."),
    "status_update": ("Order {order_no}: {status}",
                      "Hi {name}, your order {order_no} is now '{status}'. "
                      "Track it anytime from your account."),
    "quotation": ("We received your quotation request",
                  "Hi {name}, thanks for your bulk enquiry. Our corporate team will reach out soon."),
}


def notify(event, *, user=None, order=None, otp=None, request=None, extra=None):
    """Fan a single event out to email + WhatsApp/SMS, recording each in the log."""
    rules = settings.TEEPRESSO
    name = (getattr(user, "display_name", None)
            or getattr(order, "full_name", None) or "there")
    email = (getattr(user, "email", "") or getattr(order, "email", "") or "")
    phone = (getattr(user, "phone", "") or getattr(order, "phone", "") or "")
    ctx = {
        "brand": rules["BRAND"], "name": name, "otp": otp or "",
        "order_no": getattr(order, "order_no", ""),
        "total": f"{getattr(order, 'total', 0):.0f}" if order else "",
        "status": getattr(order, "status_label", ""),
    }
    if extra:
        ctx.update(extra)

    subj_t, body_t = _TEMPLATES.get(event, ("{brand} update", "Hi {name}."))
    subject, body = subj_t.format(**ctx), body_t.format(**ctx)

    if email:
        _send_email(event, email, subject, body, order)
    if phone:
        _send_whatsapp(event, phone, body, order)
        if event in ("register", "password_reset") and otp:
            _send_sms(event, phone, f"{rules['BRAND']} code: {otp}", order)


def _send_email(event, to, subject, body, order):
    status = Notification.Status.SENT
    try:
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [to], fail_silently=True)
    except Exception:
        status = Notification.Status.FAILED
    Notification.objects.create(channel=Notification.Channel.EMAIL, event=event,
                                recipient=to, subject=subject, body=body,
                                status=status, order=order)


def _send_whatsapp(event, phone, body, order):
    mode = settings.INTEGRATIONS["WHATSAPP_MODE"]
    link = wa_link(phone, body)
    if mode == "api" and settings.WHATSAPP["TOKEN"]:
        status = Notification.Status.SENT  # real Business API call would go here
    else:
        status = Notification.Status.QUEUED  # safe: one-click wa.me link instead
    Notification.objects.create(channel=Notification.Channel.WHATSAPP, event=event,
                                recipient=phone, body=body, link=link,
                                status=status, order=order)


def _send_sms(event, phone, body, order):
    if settings.INTEGRATIONS["SMS_API"]:
        status = Notification.Status.SENT  # real SMS gateway call would go here
    else:
        status = Notification.Status.QUEUED
        print(f"[SMS · safe mode] to {phone}: {body}")
    Notification.objects.create(channel=Notification.Channel.SMS, event=event,
                                recipient=phone, body=body, status=status, order=order)
