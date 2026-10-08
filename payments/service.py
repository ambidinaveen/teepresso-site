"""
Payment service — SAFE BY DEFAULT.

When INTEGRATIONS["RAZORPAY"] is False (the default), no real gateway is called
and no order is ever marked "paid" silently. The customer lands on a pay screen
where they can either pay in the (clearly-labelled) demo simulator or place the
order as an unpaid enquiry. The single swap-in point for the real Razorpay SDK is
`create_gateway_order()` / `verify_signature()` below.
"""
import base64
import io
from urllib.parse import quote

from django.conf import settings
from django.shortcuts import redirect

from .models import Payment


def start_payment(request, order):
    """Create a Payment row and route the customer to the pay screen."""
    Payment.objects.create(
        order=order, method=order.payment_method, amount=order.total,
        status=Payment.Status.CREATED, gateway_order_id=create_gateway_order(order),
    )
    return redirect("payments:pay", order_no=order.order_no)


def create_gateway_order(order):
    """Return a gateway order id. Real Razorpay call goes here when enabled."""
    if not settings.INTEGRATIONS["RAZORPAY"] or not settings.RAZORPAY["KEY_ID"]:
        return ""  # safe mode: no external call
    try:
        import razorpay
        client = razorpay.Client(auth=(settings.RAZORPAY["KEY_ID"],
                                       settings.RAZORPAY["KEY_SECRET"]))
        rp = client.order.create({
            "amount": int(order.total * 100), "currency": "INR",
            "receipt": order.order_no, "payment_capture": 1,
        })
        return rp["id"]
    except Exception:
        return ""


def verify_signature(params):
    """Verify a Razorpay callback signature. Stub returns False in safe mode."""
    if not settings.INTEGRATIONS["RAZORPAY"]:
        return False
    try:
        import razorpay
        client = razorpay.Client(auth=(settings.RAZORPAY["KEY_ID"],
                                       settings.RAZORPAY["KEY_SECRET"]))
        client.utility.verify_payment_signature(params)
        return True
    except Exception:
        return False


# ==========================================================================
# Direct UPI (PhonePe / Google Pay / Paytm / any UPI app + QR)
# ==========================================================================
#
# We build a standard UPI deep link:  upi://pay?pa=<vpa>&pn=<name>&am=<amt>...
# - `pa`  payee VPA (your business account, from settings — NEVER from client)
# - `pn`  payee name
# - `am`  amount (server-computed from the order total; the customer cannot lower it)
# - `cu`  currency (INR)
# - `tn`  transaction note
# - `tr`  transaction reference (our order number — helps reconciliation)
#
# App-specific schemes just swap the URL prefix so the branded buttons jump
# straight into that app on a phone. The generic `upi://` is used for the QR and
# the "Any UPI app" button (Android shows an app chooser).

# scheme prefixes for the branded quick-pay buttons
UPI_APPS = [
    {"key": "gpay", "label": "Google Pay", "scheme": "tez://upi/pay", "color": "#1a73e8", "icon": "google"},
    {"key": "phonepe", "label": "PhonePe", "scheme": "phonepe://pay", "color": "#5f259f", "icon": "phone"},
    {"key": "paytm", "label": "Paytm", "scheme": "paytmmp://pay", "color": "#00baf2", "icon": "wallet2"},
    {"key": "upi", "label": "Any UPI app", "scheme": "upi://pay", "color": "#0f172a", "icon": "bank"},
]


def _upi_params(order):
    """Query string shared by every UPI link — amount is always server-side."""
    cfg = settings.BUSINESS_UPI
    parts = [
        f"pa={quote(cfg['VPA'])}",
        f"pn={quote(cfg['PAYEE_NAME'])}",
        f"am={order.total:.2f}",
        "cu=INR",
        f"tn={quote('Order ' + order.order_no)}",
        f"tr={quote(order.order_no)}",
    ]
    if cfg.get("MERCHANT_CODE"):
        parts.append(f"mc={quote(cfg['MERCHANT_CODE'])}")
    return "&".join(parts)


def upi_uri(order, scheme="upi://pay"):
    """A single UPI deep link for the given app scheme."""
    return f"{scheme}?{_upi_params(order)}"


def upi_app_links(order):
    """List of {label, color, icon, uri} for the branded quick-pay buttons."""
    return [{**app, "uri": upi_uri(order, app["scheme"])} for app in UPI_APPS]


def upi_qr_data_uri(order):
    """A scannable UPI QR as a base64 PNG data-URI (generated offline)."""
    import qrcode

    img = qrcode.make(upi_uri(order), box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def record_upi_submission(order, payment, upi_ref):
    """Customer says they've paid via UPI and gives the UTR.

    SAFE: this does NOT mark the order paid. It moves the payment to
    'awaiting verification' so a staff member can confirm receipt against the
    bank/UPI statement (dashboard → order → Verify UPI payment).
    """
    from orders.models import Order

    payment.method = "upi"
    payment.upi_ref = (upi_ref or "").strip()[:40]
    payment.status = Payment.Status.AWAITING
    payment.note = f"UPI ref {payment.upi_ref} submitted by customer (unverified)"
    payment.save(update_fields=["method", "upi_ref", "status", "note"])
    order.payment_status = Order.Payment.PENDING
    order.save(update_fields=["payment_status"])


def mark_paid(order, payment, gateway_payment_id="", note=""):
    from orders.models import Order

    payment.status = Payment.Status.PAID
    payment.gateway_payment_id = gateway_payment_id
    payment.note = note
    payment.save(update_fields=["status", "gateway_payment_id", "note"])
    order.payment_status = Order.Payment.PAID
    order.save(update_fields=["payment_status"])
    order.set_status(Order.Status.CONFIRMED, note="Payment received")


def mark_enquiry(order, payment):
    from orders.models import Order

    payment.status = Payment.Status.ENQUIRY
    payment.save(update_fields=["status"])
    order.payment_status = Order.Payment.ENQUIRY
    order.save(update_fields=["payment_status"])
