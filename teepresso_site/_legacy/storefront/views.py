from django.conf import settings
from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import Customer
from catalog.models import Product, Quality, Color, Size
from catalog.pricing import quote
from orders.models import Order, OrderItem, OrderStatusEvent, Mockup, PaymentRecord


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------
def _collect_line(post):
    """Read product/quality/colour/urgent + per-size quantities from a POST.

    Returns (context_dict, error_or_None). Quantities are validated (REQ-CW-6).
    """
    try:
        product = Product.objects.get(pk=post.get("product_id"))
        quality = Quality.objects.get(pk=post.get("quality_id"))
        color = Color.objects.get(pk=post.get("color_id"))
    except (Product.DoesNotExist, Quality.DoesNotExist, Color.DoesNotExist):
        return None, "Please choose a product, quality and colour."

    urgent = post.get("urgent") in ("1", "on", "true", "True")
    items = []
    for size in Size.objects.all():
        raw = post.get(f"size_{size.id}", "").strip()
        qty = int(raw) if raw.isdigit() else 0
        if qty > 0:
            items.append({"size_id": size.id, "code": size.code, "qty": qty})

    total_qty = sum(i["qty"] for i in items)
    if total_qty <= 0:
        return None, "Please enter a quantity for at least one size."

    q = quote(total_qty, quality.price_delta, urgent)
    return {
        "product": product, "quality": quality, "color": color,
        "urgent": urgent, "items": items, "quote": q,
    }, None


def _session_customer(request):
    cid = request.session.get("customer_id")
    if cid:
        return Customer.objects.filter(pk=cid).first()
    return None


# --------------------------------------------------------------------------
# Public pages
# --------------------------------------------------------------------------
def index(request):
    products = Product.objects.filter(active=True)
    return render(request, "store/index.html", {
        "products": products,
        "customer": _session_customer(request),
    })


def configurator(request, product_id):
    product = get_object_or_404(Product, pk=product_id, active=True)
    return render(request, "store/configurator.html", {
        "product": product,
        "qualities": Quality.objects.filter(active=True),
        "colors": Color.objects.filter(active=True),
        "sizes": Size.objects.all(),
        "customer": _session_customer(request),
    })


def price_api(request):
    """Live pricing endpoint for the JS configurator (REQ-CW-9, <200ms)."""
    qty = request.GET.get("qty", 0)
    urgent = request.GET.get("urgent") in ("1", "true", "True")
    delta = 0
    qid = request.GET.get("quality_id")
    if qid:
        qobj = Quality.objects.filter(pk=qid).first()
        if qobj:
            delta = qobj.price_delta
    return JsonResponse(quote(qty, delta, urgent))


def register(request):
    """Registration popup — Name + Phone only (REQ-CW-1/2)."""
    if request.method != "POST":
        return JsonResponse({"ok": False}, status=405)
    name = (request.POST.get("name") or "").strip()
    phone = "".join(c for c in (request.POST.get("phone") or "") if c.isdigit())
    if not name or len(phone) < 10:
        return JsonResponse({"ok": False, "error": "Enter a valid name and phone."}, status=400)
    customer, _ = Customer.objects.get_or_create(phone=phone, defaults={"name": name})
    if customer.name != name and name:
        customer.name = name
        customer.save(update_fields=["name"])
    request.session["customer_id"] = customer.id
    return JsonResponse({"ok": True, "name": customer.name, "phone": customer.phone})


def checkout(request):
    """Build the order draft from the configurator and show checkout."""
    if request.method != "POST":
        return redirect("storefront:index")
    line, error = _collect_line(request.POST)
    if error:
        messages.error(request, error)
        return redirect("storefront:configurator", product_id=request.POST.get("product_id") or 0)

    request.session["draft"] = {
        "product_id": line["product"].id,
        "quality_id": line["quality"].id,
        "color_id": line["color"].id,
        "urgent": line["urgent"],
        "items": line["items"],
        "wants_mockup": request.POST.get("wants_mockup") in ("1", "on", "true"),
        "design_json": request.POST.get("design_json", ""),
        "design_preview": request.POST.get("design_preview", ""),
    }
    return render(request, "store/checkout.html", {
        "line": line,
        "customer": _session_customer(request),
        "online_payments": settings.INTEGRATIONS["ONLINE_PAYMENTS"],
    })


def place_order(request):
    """Create the order. SAFE: if online payments are OFF, the order is recorded
    as an UNPAID ENQUIRY — never a fake 'paid' order (REQ-CW-16/18, safe mode)."""
    if request.method != "POST":
        return redirect("storefront:index")

    draft = request.session.get("draft")
    if not draft:
        messages.error(request, "Your session expired. Please configure again.")
        return redirect("storefront:index")

    # customer (from popup, or captured here)
    name = (request.POST.get("name") or "").strip()
    phone = "".join(c for c in (request.POST.get("phone") or "") if c.isdigit())
    address = (request.POST.get("address") or "").strip()
    if len(phone) < 10 or not name or not address:
        messages.error(request, "Please enter name, phone and delivery address.")
        return render(request, "store/checkout.html", {
            "line": _rebuild_line(draft),
            "customer": _session_customer(request),
            "online_payments": settings.INTEGRATIONS["ONLINE_PAYMENTS"],
        })
    customer, _ = Customer.objects.get_or_create(phone=phone, defaults={"name": name})

    line = _rebuild_line(draft)
    q = line["quote"]

    order = Order(
        customer=customer,
        channel=Order.Channel.ONLINE,
        product=line["product"], quality=line["quality"], color=line["color"],
        urgent=line["urgent"], address=address,
        wants_mockup=draft.get("wants_mockup", False),
        design_json=draft.get("design_json", ""),
        design_preview=draft.get("design_preview", ""),
        status=Order.Status.NEW,
    )
    order.apply_quote(q)

    # SAFE payment handling -------------------------------------------------
    if settings.INTEGRATIONS["ONLINE_PAYMENTS"]:
        # Real gateway flow would capture here; left as the single swap-in point.
        order.payment_status = Order.Payment.PAID
        pay_status = "paid"
    else:
        order.payment_status = Order.Payment.ENQUIRY   # unpaid enquiry, not fake-paid
        pay_status = "unpaid"
    order.save()

    for it in line["items"]:
        OrderItem.objects.create(
            order=order, size_id=it["size_id"], qty=it["qty"],
            unit_price=q["unit_price"],
        )
    PaymentRecord.objects.create(order=order, method="upi", status=pay_status, amount=q["total"])
    OrderStatusEvent.objects.create(order=order, status=order.status, note="Order placed")
    if order.wants_mockup:
        Mockup.objects.create(order=order, kind="teepresso", title="Mockup requested")

    # Auto-generate the bill and send it to the customer's WhatsApp (safe mode:
    # queued with a one-click link; API mode: sent automatically).
    from messaging.service import send_bill
    send_bill(order, request=request)

    request.session.pop("draft", None)
    request.session["customer_id"] = customer.id
    return redirect("storefront:confirmation", order_no=order.order_no)


def _rebuild_line(draft):
    product = Product.objects.get(pk=draft["product_id"])
    quality = Quality.objects.get(pk=draft["quality_id"])
    color = Color.objects.get(pk=draft["color_id"])
    items = draft["items"]
    total_qty = sum(i["qty"] for i in items)
    q = quote(total_qty, quality.price_delta, draft["urgent"])
    return {"product": product, "quality": quality, "color": color,
            "urgent": draft["urgent"], "items": items, "quote": q}


def confirmation(request, order_no):
    order = get_object_or_404(Order, order_no=order_no)
    wa = order.messages.filter(kind="bill").first()
    return render(request, "store/confirmation.html", {"order": order, "wa": wa})


def bill(request, order_no):
    """Public GST bill / invoice for an order (the link sent on WhatsApp)."""
    order = get_object_or_404(Order.objects.select_related("customer"), order_no=order_no)
    gst_half = round(order.gst / 2)
    return render(request, "store/bill.html", {
        "order": order,
        "items": order.items.select_related("size").all(),
        "cgst": gst_half,
        "sgst": order.gst - gst_half,
        "taxable": order.subtotal + order.urgent_charge,
    })


def tracking(request, order_no=None):
    order = None
    if request.method == "POST":
        order_no = (request.POST.get("order_no") or "").strip()
    if order_no:
        order = Order.objects.filter(order_no=order_no).first()
        if not order and request.method == "POST":
            messages.error(request, "No order found with that number.")
    timeline = []
    if order:
        flow = [Order.Status.NEW, Order.Status.DESIGN, Order.Status.PRODUCTION,
                Order.Status.QC, Order.Status.DISPATCHED, Order.Status.DELIVERED]
        current_index = flow.index(order.status) if order.status in flow else 0
        labels = dict(Order.Status.choices)
        for i, st in enumerate(flow):
            timeline.append({
                "label": labels[st],
                "done": i < current_index,
                "active": i == current_index,
            })
    return render(request, "store/tracking.html", {"order": order, "timeline": timeline})
