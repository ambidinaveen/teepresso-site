from django.conf import settings
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from cart.utils import get_cart
from notifications.service import notify
from payments.service import start_payment

from .models import Invoice, Order, OrderItem


def checkout(request):
    cart = get_cart(request)
    items = cart.items.filter(saved_for_later=False).select_related("product", "design")
    if not items:
        messages.info(request, "Your cart is empty.")
        return redirect("products:list")

    user = request.user if request.user.is_authenticated else None
    if request.method == "POST":
        return _place_order(request, cart, items)

    prefill = {}
    if user:
        addr = user.default_address
        prefill = {
            "full_name": user.get_full_name() or user.display_name,
            "email": user.email, "phone": user.phone,
            "company": user.company, "gst_number": user.gst_number,
        }
        if addr:
            prefill["shipping_address"] = addr.one_line
    return render(request, "store/checkout.html", {
        "cart": cart, "items": items, "prefill": prefill,
        "addresses": user.addresses.all() if user else [],
        "razorpay_on": settings.INTEGRATIONS["RAZORPAY"],
        "upi_on": settings.INTEGRATIONS.get("UPI") and settings.BUSINESS_UPI["VPA"],
    })


@transaction.atomic
def _place_order(request, cart, items):
    p = request.POST
    full_name = (p.get("full_name") or "").strip()
    phone = "".join(c for c in (p.get("phone") or "") if c.isdigit())
    shipping = (p.get("shipping_address") or "").strip()
    if not full_name or len(phone) < 10 or not shipping:
        messages.error(request, "Please provide name, a valid phone, and a delivery address.")
        return redirect("orders:checkout")

    order = Order.objects.create(
        user=request.user if request.user.is_authenticated else None,
        full_name=full_name, email=(p.get("email") or "").strip(), phone=phone,
        company=(p.get("company") or "").strip(), gst_number=(p.get("gst_number") or "").strip(),
        billing_address=(p.get("billing_address") or shipping).strip(),
        shipping_address=shipping,
        subtotal=cart.subtotal, discount=cart.discount, gst=cart.gst,
        shipping=cart.shipping, total=cart.total,
        coupon_code=cart.coupon.code if cart.coupon else "",
        payment_method=p.get("payment_method", "razorpay"),
    )
    for it in items:
        OrderItem.objects.create(
            order=order, product=it.product, design=it.design, name=it.product.name,
            variant_label=it.variant_label, qty=it.qty, unit_price=it.unit_price,
        )
        Product = it.product.__class__
        Product.objects.filter(pk=it.product_id).update(sold_count=it.product.sold_count + it.qty)
        inv = getattr(it.product, "inventory", None)
        if inv:
            inv.quantity = max(inv.quantity - it.qty, 0)
            inv.save(update_fields=["quantity"])

    order.eway_required = order.needs_eway
    order.save(update_fields=["eway_required"])
    Invoice.objects.create(order=order)
    order.set_status(Order.Status.PENDING, note="Order placed")

    if cart.coupon:
        cart.coupon.used_count += 1
        cart.coupon.save(update_fields=["used_count"])

    # clear the cart
    cart.items.all().delete()
    cart.coupon = None
    cart.save(update_fields=["coupon"])

    notify("order_placed", order=order, request=request)

    # SAFE payment handling: real gateway only when RAZORPAY is enabled.
    return start_payment(request, order)


def confirmation(request, order_no):
    order = get_object_or_404(Order.objects.prefetch_related("items"), order_no=order_no)
    wa = notify_link(order)
    return render(request, "store/confirmation.html", {"order": order, "wa": wa})


def notify_link(order):
    from core.utils import wa_link
    text = (f"Hi, my Teepresso order {order.order_no} total ₹{order.total:.0f} "
            f"is placed. Please confirm.")
    return wa_link(order.phone or settings.TEEPRESSO["SUPPORT_PHONE"], text)


def invoice(request, order_no):
    order = get_object_or_404(Order.objects.prefetch_related("items"), order_no=order_no)
    if request.user.is_authenticated and not request.user.is_staff_role \
            and order.user_id and order.user_id != request.user.id:
        messages.error(request, "You can only view your own invoices.")
        return redirect("accounts:orders")
    inv = getattr(order, "invoice", None) or Invoice.objects.create(order=order)
    gst_half = (order.gst / 2)
    return render(request, "store/invoice.html", {
        "order": order, "invoice": inv,
        "cgst": gst_half, "sgst": order.gst - gst_half,
        "taxable": order.subtotal - order.discount,
    })


def track(request, order_no=None):
    order = None
    if request.method == "POST":
        order_no = (request.POST.get("order_no") or "").strip()
    if order_no:
        order = Order.objects.filter(order_no=order_no).first()
        if not order and request.method == "POST":
            messages.error(request, "No order found with that number.")
    return render(request, "store/tracking.html", {
        "order": order, "timeline": order.timeline() if order else [],
    })
