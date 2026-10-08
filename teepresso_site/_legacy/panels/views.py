from datetime import timedelta

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.db.models import Count, Sum
from django.db.models.functions import TruncMonth
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import Attendance
from catalog.models import Product, Quality, Color, Size
from catalog.pricing import quote
from inventory.models import StockItem, StockMovement
from orders.models import (
    Order, OrderItem, OrderStatusEvent, Mockup, PaymentRecord, Shipment,
)
from storefront.utils import wa_link

from .access import role_required

Role = None  # set lazily to avoid import cycle issues


# --------------------------------------------------------------------------
# Auth
# --------------------------------------------------------------------------
def login_view(request):
    if request.user.is_authenticated:
        return redirect("panels:home")
    if request.method == "POST":
        user = authenticate(
            request,
            username=request.POST.get("username"),
            password=request.POST.get("password"),
        )
        if user is not None:
            login(request, user)  # fires attendance login signal
            return redirect("panels:home")
        messages.error(request, "Invalid username or password.")
    return render(request, "panels/login.html")


def logout_view(request):
    logout(request)  # fires attendance logout signal
    return redirect("panels:login")


def home_redirect(request):
    if not request.user.is_authenticated:
        return redirect("panels:login")
    if request.user.is_superuser:
        return redirect("panels:admin_dashboard")
    return redirect(request.user.home_url_name)


# --------------------------------------------------------------------------
# Admin
# --------------------------------------------------------------------------
@role_required("admin")
def admin_dashboard(request):
    paid = Order.objects.exclude(status=Order.Status.CANCELLED)
    revenue = paid.aggregate(s=Sum("total"))["s"] or 0
    order_count = paid.count()
    aov = round(revenue / order_count) if order_count else 0

    # Placeholder P&L (no cost data yet — clearly flagged in the UI)
    cogs = round(revenue * 0.55)
    opex = round(revenue * 0.18)
    net_profit = revenue - cogs - opex

    # Monthly sales for the chart
    monthly = (
        paid.annotate(m=TruncMonth("created_at"))
        .values("m").annotate(total=Sum("total")).order_by("m")
    )
    months = [{"label": row["m"].strftime("%b %y"), "total": row["total"] or 0}
              for row in monthly if row["m"]]

    today = timezone.localdate()
    attendance = Attendance.objects.filter(login_ts__date=today).select_related("user")

    return render(request, "panels/admin_dashboard.html", {
        "revenue": revenue, "order_count": order_count, "aov": aov,
        "cogs": cogs, "opex": opex, "net_profit": net_profit,
        "months": months, "max_month": max([m["total"] for m in months], default=1) or 1,
        "recent_orders": paid.select_related("customer")[:8],
        "urgent_count": paid.filter(urgent=True).count(),
        "bulk_count": sum(1 for o in paid if o.is_bulk),
        "attendance": attendance,
        "active": "dashboard",
    })


@role_required("admin")
def order_management(request):
    f = request.GET.get("filter", "all")
    orders = Order.objects.select_related("customer").all()
    if f == "urgent":
        orders = orders.filter(urgent=True)
    elif f == "new":
        orders = orders.filter(status=Order.Status.NEW)
    elif f == "production":
        orders = orders.filter(status=Order.Status.PRODUCTION)
    elif f == "qc":
        orders = orders.filter(status=Order.Status.QC)
    elif f == "dispatched":
        orders = orders.filter(status=Order.Status.DISPATCHED)

    orders = list(orders[:100])
    if f == "bulk":
        orders = [o for o in orders if o.is_bulk]

    return render(request, "panels/order_management.html", {
        "orders": orders,
        "filter": f,
        "stats": {
            "new": Order.objects.filter(status=Order.Status.NEW).count(),
            "urgent": Order.objects.filter(urgent=True).count(),
            "bulk": sum(1 for o in Order.objects.all() if o.is_bulk),
            "qc": Order.objects.filter(status=Order.Status.QC).count(),
        },
        "statuses": Order.Status.choices,
        "active": "orders",
    })


@role_required("admin")
def orders_api(request):
    """Lightweight count endpoint the live screen polls (REQ-OM-2)."""
    from django.http import JsonResponse
    return JsonResponse({"count": Order.objects.count()})


@role_required("admin")
def update_status(request, order_no):
    order = get_object_or_404(Order, order_no=order_no)
    if request.method == "POST":
        new = request.POST.get("status")
        valid = dict(Order.Status.choices)
        if new in valid:
            order.status = new
            order.save(update_fields=["status"])
            OrderStatusEvent.objects.create(
                order=order, status=new, actor=request.user, note="Status updated"
            )
            messages.success(request, f"{order.order_no} → {valid[new]}")
    return redirect("panels:order_management")


# --------------------------------------------------------------------------
# Manager (LIMITED — no prices / no customer contact in the order view: REQ-MGR-3)
# --------------------------------------------------------------------------
@role_required("admin", "manager")
def manager_inventory(request):
    items = StockItem.objects.select_related("product", "quality", "color", "size").all()
    low = [i for i in items if i.status in ("low", "out")]
    movements = StockMovement.objects.select_related("item", "by")[:8]
    offline = Order.objects.filter(channel=Order.Channel.OFFLINE).select_related("customer")[:8]

    # Limited order view: only order_no, qty, status (no money / contact)
    order_status = Order.objects.values("order_no", "qty_total", "status")[:10]

    return render(request, "panels/manager_inventory.html", {
        "items": items,
        "low_count": len(low),
        "movements": movements,
        "offline_orders": offline,
        "order_status": order_status,
        "status_labels": dict(Order.Status.choices),
        "active": "inventory",
    })


@role_required("admin", "manager")
def stock_action(request):
    if request.method == "POST":
        item = get_object_or_404(StockItem, pk=request.POST.get("item_id"))
        kind = request.POST.get("kind")
        qty = int(request.POST.get("qty") or 0)
        if qty > 0 and kind in ("in", "out"):
            mv = StockMovement(item=item, kind=kind, qty=qty, by=request.user)
            mv.apply()
            messages.success(request, f"Stock {kind.upper()} {qty} → {item.sku}")
    return redirect("panels:manager_inventory")


@role_required("admin", "manager")
def offline_order(request):
    """Create a walk-in/phone order with manual QR collection + auto bill (REQ-OFF)."""
    if request.method == "POST":
        from accounts.models import Customer
        name = (request.POST.get("name") or "Walk-in").strip()
        phone = "".join(c for c in (request.POST.get("phone") or "") if c.isdigit()) or "0000000000"
        product = Product.objects.first()
        quality = Quality.objects.first()
        color = Color.objects.first()
        qty = int(request.POST.get("qty") or 0)
        if qty <= 0 or not (product and quality and color):
            messages.error(request, "Enter a quantity (and ensure catalog is seeded).")
            return redirect("panels:manager_inventory")
        customer, _ = Customer.objects.get_or_create(phone=phone, defaults={"name": name})
        q = quote(qty, quality.price_delta, False)
        order = Order(customer=customer, channel=Order.Channel.OFFLINE,
                      product=product, quality=quality, color=color,
                      payment_status=Order.Payment.PAID, status=Order.Status.NEW)
        order.apply_quote(q)
        order.save()
        OrderItem.objects.create(order=order, size=Size.objects.first(), qty=qty,
                                 unit_price=q["unit_price"])
        PaymentRecord.objects.create(order=order, method="qr", status="paid", amount=q["total"])
        OrderStatusEvent.objects.create(order=order, status=order.status, note="Offline order (QR)")
        # auto-generate the bill and send/queue it to the customer's WhatsApp
        from messaging.service import send_bill
        send_bill(order, request=request)
        messages.success(request, f"Offline order {order.order_no} created · bill auto-sent to WhatsApp · ₹{q['total']:,}")
    return redirect("panels:manager_inventory")


# --------------------------------------------------------------------------
# Editor — sees the customer's own design (text + photo) for each order.
# Files editor-only; approval over WhatsApp moves the order to production.
# --------------------------------------------------------------------------
@role_required("admin", "editor")
def editor_mockups(request):
    orders = (Order.objects
              .exclude(status__in=[Order.Status.DISPATCHED, Order.Status.DELIVERED, Order.Status.CANCELLED])
              .select_related("customer").order_by("-created_at"))
    cards = []
    for o in orders[:18]:
        text = (f"Hi {o.customer.name}, here's your Teepresso mockup for order "
                f"{o.order_no}. Reply YES to approve.")
        cards.append({"o": o, "wa": wa_link(o.customer.phone, text),
                      "has_design": bool(o.design_preview)})
    return render(request, "panels/editor_mockups.html", {
        "cards": cards,
        "pending": orders.filter(status=Order.Status.NEW).count(),
        "approved": Order.objects.filter(status=Order.Status.PRODUCTION).count(),
        "active": "mockups",
    })


@role_required("admin", "editor")
def mockup_approve(request, order_no):
    """Approve the customer's design (over WhatsApp) → order goes to production."""
    order = get_object_or_404(Order, order_no=order_no)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "approve":
            order.mockups.update(approval_status=Mockup.Approval.APPROVED, watermarked=False)
            if order.status == Order.Status.NEW:
                order.status = Order.Status.PRODUCTION
                order.save(update_fields=["status"])
            OrderStatusEvent.objects.create(order=order, status=order.status,
                                            actor=request.user, note="Design approved on WhatsApp")
            messages.success(request, f"{order.order_no} approved → Production.")
        elif action == "decline":
            order.mockups.update(approval_status=Mockup.Approval.DECLINED)
            messages.info(request, f"{order.order_no} marked for revision.")
    return redirect("panels:editor_mockups")


@role_required("admin", "editor")
def order_detail(request, order_no):
    """Full order + the customer's exact design (text items + preview)."""
    order = get_object_or_404(Order.objects.select_related("customer"), order_no=order_no)
    text_items = []
    if order.design_json:
        import json
        try:
            data = json.loads(order.design_json)
            for obj in data.get("objects", []):
                if obj.get("type") in ("i-text", "text", "textbox"):
                    text_items.append({
                        "text": obj.get("text", ""),
                        "color": obj.get("fill", "#000"),
                        "font": obj.get("fontFamily", ""),
                        "size": round(obj.get("fontSize", 0) * obj.get("scaleY", 1)),
                    })
        except (ValueError, TypeError):
            pass
    return render(request, "panels/order_detail.html", {
        "order": order,
        "items": order.items.select_related("size").all(),
        "text_items": text_items,
        "bill_msg": order.messages.filter(kind="bill").first(),
        "eway_threshold": settings.TEEPRESSO["EWAY_THRESHOLD"],
        "active": "orders",
    })


@role_required("admin", "manager")
def send_bill_action(request, order_no):
    """(Re)generate the bill and send/queue it to the customer's WhatsApp."""
    order = get_object_or_404(Order, order_no=order_no)
    if request.method == "POST":
        from messaging.service import send_bill
        msg = send_bill(order, request=request)
        if msg.status == "sent":
            messages.success(request, f"Bill sent to {order.customer.name}'s WhatsApp.")
        else:
            messages.info(request, "Bill ready — use the WhatsApp button to send it.")
    return redirect("panels:order_detail", order_no=order.order_no)


# --------------------------------------------------------------------------
# Dispatch (piece count, QC, label, invoice, E-Way RULE — flagged, not faked)
# --------------------------------------------------------------------------
@role_required("admin", "dispatch")
def dispatch(request):
    queue = Order.objects.filter(
        status__in=[Order.Status.PRODUCTION, Order.Status.QC]
    ).select_related("customer")
    rows = []
    for o in queue[:50]:
        sh = getattr(o, "shipment", None)
        rows.append({"o": o, "sh": sh})
    return render(request, "panels/dispatch.html", {
        "rows": rows,
        "eway_threshold": settings.TEEPRESSO["EWAY_THRESHOLD"],
        "eway_api_on": settings.INTEGRATIONS["EWAY_API"],
        "stats": {
            "ready": queue.count(),
            "shipped_today": Order.objects.filter(
                status=Order.Status.DISPATCHED, created_at__date=timezone.localdate()
            ).count(),
        },
        "active": "dispatch",
    })


@role_required("admin", "dispatch")
def dispatch_process(request, order_no):
    order = get_object_or_404(Order, order_no=order_no)
    if request.method == "POST":
        sh, _ = Shipment.objects.get_or_create(order=order)
        sh.piece_count_verified = int(request.POST.get("piece_count") or 0)
        sh.qc_result = request.POST.get("qc_result", Shipment.QC.PENDING)
        action = request.POST.get("action")

        # Piece count must match total; QC must pass before dispatch
        if action == "dispatch":
            if sh.piece_count_verified != order.qty_total:
                messages.error(request, f"Piece count {sh.piece_count_verified} ≠ ordered {order.qty_total}. Cannot dispatch.")
                sh.save(); return redirect("panels:dispatch")
            if sh.qc_result != Shipment.QC.PASS:
                messages.error(request, "QC must pass before dispatch.")
                sh.save(); return redirect("panels:dispatch")

            # Invoice (internal GST doc) + E-Way RULE
            sh.invoice_no = sh.invoice_no or f"INV-{order.order_no[3:]}"
            sh.awb = (request.POST.get("awb") or "").strip()
            if order.needs_eway:
                sh.eway_required = True
                if settings.INTEGRATIONS["EWAY_API"]:
                    sh.eway_no = f"EWB{order.order_no[3:]}"   # real GSP call goes here
                # else: stays flagged, no fake number issued (safe)
            order.status = Order.Status.DISPATCHED
            order.save(update_fields=["status"])
            sh.dispatched = True
            OrderStatusEvent.objects.create(order=order, status=order.status,
                                            actor=request.user, note="Dispatched")
            messages.success(request, f"{order.order_no} dispatched · invoice {sh.invoice_no}"
                                      + (" · E-Way required" if sh.eway_required and not sh.eway_no else ""))
        sh.save()
    return redirect("panels:dispatch")
