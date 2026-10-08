from django.conf import settings
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from core.utils import wa_link
from notifications.service import notify
from orders.models import Order

from .models import Payment
from .service import (
    mark_enquiry,
    mark_paid,
    record_upi_submission,
    upi_app_links,
    upi_qr_data_uri,
    verify_signature,
)


def pay(request, order_no):
    order = get_object_or_404(Order, order_no=order_no)
    payment = order.payments.first()
    upi_on = settings.INTEGRATIONS.get("UPI") and settings.BUSINESS_UPI["VPA"]

    ctx = {
        "order": order, "payment": payment,
        "razorpay_on": settings.INTEGRATIONS["RAZORPAY"],
        "razorpay_key": settings.RAZORPAY["KEY_ID"],
        "upi_on": upi_on,
    }
    if upi_on:
        note = (f"Hi, I've paid ₹{order.total:.0f} for order {order.order_no} via UPI. "
                f"Here is my payment screenshot / reference.")
        ctx.update({
            "upi_vpa": settings.BUSINESS_UPI["VPA"],
            "upi_name": settings.BUSINESS_UPI["PAYEE_NAME"],
            "upi_placeholder": settings.BUSINESS_UPI["IS_PLACEHOLDER"],
            "upi_apps": upi_app_links(order),
            "upi_qr": upi_qr_data_uri(order),
            "upi_wa": wa_link(settings.TEEPRESSO["SUPPORT_PHONE"], note),
        })
    return render(request, "store/pay.html", ctx)


def upi_confirm(request, order_no):
    """Customer reports they've paid via UPI and submits the reference (UTR).

    SAFE: never marks the order paid — a staff member verifies receipt first.
    """
    order = get_object_or_404(Order, order_no=order_no)
    if request.method != "POST":
        return redirect("payments:pay", order_no=order_no)
    payment = order.payments.first()
    ref = (request.POST.get("upi_ref") or "").strip()
    if len(ref) < 6:
        messages.error(request, "Please enter the UPI reference / UTR number shown in your UPI app.")
        return redirect("payments:pay", order_no=order_no)
    record_upi_submission(order, payment, ref)
    notify("payment_pending", order=order, request=request)
    messages.success(
        request,
        "Thanks! We've recorded your UPI reference. Our team will verify the payment "
        "and confirm your order shortly.",
    )
    return redirect("orders:confirmation", order_no=order.order_no)


def simulate_success(request, order_no):
    """Demo-only success path (visible only when Razorpay is OFF)."""
    order = get_object_or_404(Order, order_no=order_no)
    if settings.INTEGRATIONS["RAZORPAY"]:
        return redirect("payments:pay", order_no=order_no)
    payment = order.payments.first()
    mark_paid(order, payment, note="Demo simulator payment")
    notify("payment_success", order=order, request=request)
    messages.success(request, "Payment successful (demo). Your order is confirmed!")
    return redirect("orders:confirmation", order_no=order.order_no)


def place_as_enquiry(request, order_no):
    order = get_object_or_404(Order, order_no=order_no)
    payment = order.payments.first()
    mark_enquiry(order, payment)
    messages.info(request, "Order placed as an enquiry. Our team will contact you to collect payment.")
    return redirect("orders:confirmation", order_no=order.order_no)


def callback(request):
    """Razorpay browser callback (used only when Razorpay is enabled)."""
    order_no = request.POST.get("order_no", "")
    order = get_object_or_404(Order, order_no=order_no)
    payment = order.payments.first()
    params = {
        "razorpay_order_id": request.POST.get("razorpay_order_id", ""),
        "razorpay_payment_id": request.POST.get("razorpay_payment_id", ""),
        "razorpay_signature": request.POST.get("razorpay_signature", ""),
    }
    if verify_signature(params):
        mark_paid(order, payment, gateway_payment_id=params["razorpay_payment_id"])
        notify("payment_success", order=order, request=request)
        messages.success(request, "Payment successful! Your order is confirmed.")
    else:
        payment.status = Payment.Status.FAILED
        payment.save(update_fields=["status"])
        order.payment_status = Order.Payment.FAILED
        order.save(update_fields=["payment_status"])
        messages.error(request, "Payment could not be verified.")
    return redirect("orders:confirmation", order_no=order.order_no)
