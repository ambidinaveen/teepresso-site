import csv
import json
from datetime import timedelta

from django.contrib import messages
from django.db.models import Count, Q, Sum
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from accounts.models import User
from blogs.models import Blog
from cart.models import Coupon
from cms.models import FAQ, Banner, ContactMessage, Testimonial
from core.models import AuditLog
from notifications.models import Notification
from orders.models import Order
from products.models import CustomDesign, Inventory, Product
from quotations.models import CorporateLead

from .access import role_required, staff_required
from .forms import (BannerForm, BlogForm, CouponForm, FAQForm, ProductForm,
                    TestimonialForm)

PAID = [Order.Payment.PAID]


# --- Dashboard home / analytics ------------------------------------------
@staff_required
def home(request):
    orders = Order.objects.all()
    paid = orders.filter(payment_status=Order.Payment.PAID)
    revenue = paid.aggregate(s=Sum("total"))["s"] or 0
    customers = User.objects.filter(role__in=[User.Role.CUSTOMER, User.Role.CORPORATE])
    leads = CorporateLead.objects.all()

    # monthly sales (last 6 months)
    today = timezone.localdate()
    months, sales_series, orders_series = [], [], []
    for i in range(5, -1, -1):
        m = (today.replace(day=1) - timedelta(days=i * 30)).replace(day=1)
        nxt = (m + timedelta(days=32)).replace(day=1)
        mo = paid.filter(created_at__date__gte=m, created_at__date__lt=nxt)
        months.append(m.strftime("%b"))
        sales_series.append(float(mo.aggregate(s=Sum("total"))["s"] or 0))
        orders_series.append(orders.filter(created_at__date__gte=m,
                                            created_at__date__lt=nxt).count())

    top_products = (Product.objects.order_by("-sold_count")[:6])
    status_counts = {s.label: orders.filter(status=s.value).count() for s in Order.Status}

    ctx = {
        "revenue": revenue,
        "order_count": orders.count(),
        "customer_count": customers.count(),
        "lead_count": leads.count(),
        "pending_orders": orders.exclude(
            status__in=[Order.Status.DELIVERED, Order.Status.CANCELLED]).count(),
        "conversion": round((paid.count() / orders.count() * 100) if orders.count() else 0, 1),
        "recent_orders": orders[:8],
        "new_leads": leads.filter(status=CorporateLead.Status.NEW)[:5],
        "low_stock": Inventory.objects.filter(
            quantity__lte=10).select_related("product")[:5],
        "pending_designs": CustomDesign.objects.filter(
            status=CustomDesign.Status.PENDING).count(),
        "chart_months": json.dumps(months),
        "chart_sales": json.dumps(sales_series),
        "chart_orders": json.dumps(orders_series),
        "chart_products": json.dumps([p.name for p in top_products]),
        "chart_product_sales": json.dumps([p.sold_count for p in top_products]),
        "status_counts": status_counts,
        "section": "home",
    }
    return render(request, "dashboard/home.html", ctx)


# --- Orders ---------------------------------------------------------------
@staff_required
def orders_list(request):
    qs = Order.objects.all().prefetch_related("items")
    status = request.GET.get("status")
    if status:
        qs = qs.filter(status=status)
    q = request.GET.get("q")
    if q:
        qs = qs.filter(Q(order_no__icontains=q) | Q(full_name__icontains=q) |
                       Q(phone__icontains=q))
    return render(request, "dashboard/orders.html", {
        "orders": qs[:100], "statuses": Order.Status.choices,
        "active_status": status, "q": q or "", "section": "orders",
    })


@staff_required
def order_detail(request, order_no):
    order = get_object_or_404(Order, order_no=order_no)
    if request.method == "POST":
        action = request.POST.get("action")
        if action == "status":
            new = request.POST.get("status")
            order.set_status(new, actor=request.user, note=request.POST.get("note", ""))
            from notifications.service import notify
            notify("status_update", order=order, request=request)
            messages.success(request, f"Status updated to {order.status_label}.")
        elif action == "tracking":
            order.tracking_number = request.POST.get("tracking_number", "")
            order.courier = request.POST.get("courier", "")
            order.save(update_fields=["tracking_number", "courier"])
            messages.success(request, "Tracking details saved.")
        elif action == "verify_payment":
            from payments.service import mark_paid
            payment = order.payments.first()
            if payment:
                mark_paid(order, payment, note="UPI payment verified by staff")
                from notifications.service import notify
                notify("payment_success", order=order, request=request)
                messages.success(request, "Payment verified — order marked as paid & confirmed.")
            else:
                messages.error(request, "No payment record found for this order.")
        return redirect("dashboard:order_detail", order_no=order.order_no)
    return render(request, "dashboard/order_detail.html", {
        "order": order, "statuses": Order.Status.choices,
        "timeline": order.timeline(), "section": "orders",
        "payment": order.payments.first(),
    })


# --- Products -------------------------------------------------------------
@role_required(User.Role.ADMIN, User.Role.PRODUCT_MANAGER)
def products_list(request):
    qs = Product.objects.select_related("category")
    q = request.GET.get("q")
    if q:
        qs = qs.filter(name__icontains=q)
    return render(request, "dashboard/products.html",
                  {"products": qs[:200], "q": q or "", "section": "products"})


@role_required(User.Role.ADMIN, User.Role.PRODUCT_MANAGER)
def product_edit(request, pk=None):
    product = get_object_or_404(Product, pk=pk) if pk else None
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if request.method == "POST" and form.is_valid():
        obj = form.save()
        Inventory.objects.get_or_create(product=obj)
        messages.success(request, "Product saved.")
        return redirect("dashboard:products")
    return render(request, "dashboard/product_form.html",
                  {"form": form, "product": product, "section": "products"})


@role_required(User.Role.ADMIN, User.Role.PRODUCT_MANAGER)
def product_delete(request, pk):
    Product.objects.filter(pk=pk).update(active=False)
    messages.info(request, "Product deactivated.")
    return redirect("dashboard:products")


# --- Inventory ------------------------------------------------------------
@role_required(User.Role.ADMIN, User.Role.PRODUCT_MANAGER)
def inventory(request):
    if request.method == "POST":
        for key, val in request.POST.items():
            if key.startswith("qty_") and val.isdigit():
                pid = key.split("_", 1)[1]
                inv, _ = Inventory.objects.get_or_create(product_id=pid)
                inv.quantity = int(val)
                inv.save(update_fields=["quantity"])
        messages.success(request, "Inventory updated.")
        return redirect("dashboard:inventory")
    items = Inventory.objects.select_related("product").order_by("quantity")
    return render(request, "dashboard/inventory.html",
                  {"items": items, "section": "inventory"})


# --- Customers ------------------------------------------------------------
@role_required(User.Role.ADMIN, User.Role.SUPPORT)
def customers(request):
    qs = User.objects.filter(role__in=[User.Role.CUSTOMER, User.Role.CORPORATE])
    q = request.GET.get("q")
    if q:
        qs = qs.filter(Q(email__icontains=q) | Q(phone__icontains=q) |
                       Q(first_name__icontains=q))
    qs = qs.annotate(order_count=Count("orders"))
    return render(request, "dashboard/customers.html",
                  {"customers": qs[:200], "q": q or "", "section": "customers"})


@role_required(User.Role.ADMIN, User.Role.SUPPORT)
def customer_toggle_block(request, pk):
    u = get_object_or_404(User, pk=pk)
    u.is_blocked = not u.is_blocked
    u.save(update_fields=["is_blocked"])
    messages.success(request, f"{'Blocked' if u.is_blocked else 'Unblocked'} {u.email}.")
    return redirect("dashboard:customers")


# --- Corporate leads ------------------------------------------------------
@staff_required
def leads(request):
    qs = CorporateLead.objects.select_related("assigned_to")
    status = request.GET.get("status")
    if status:
        qs = qs.filter(status=status)
    return render(request, "dashboard/leads.html", {
        "leads": qs[:200], "statuses": CorporateLead.Status.choices,
        "staff": User.objects.filter(role__in=User.STAFF_ROLES),
        "active_status": status, "section": "leads",
    })


@staff_required
def lead_update(request, pk):
    lead = get_object_or_404(CorporateLead, pk=pk)
    if request.method == "POST":
        lead.status = request.POST.get("status", lead.status)
        assignee = request.POST.get("assigned_to")
        lead.assigned_to = User.objects.filter(pk=assignee).first() if assignee else None
        lead.followup_note = request.POST.get("followup_note", lead.followup_note)
        lead.save()
        messages.success(request, "Lead updated.")
    return redirect("dashboard:leads")


# --- Coupons --------------------------------------------------------------
@role_required(User.Role.ADMIN)
def coupons(request):
    form = CouponForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Coupon created.")
        return redirect("dashboard:coupons")
    return render(request, "dashboard/coupons.html",
                  {"coupons": Coupon.objects.all(), "form": form, "section": "coupons"})


# --- CMS / content --------------------------------------------------------
_CMS_MAP = {
    "banners": (Banner, BannerForm, "Banners"),
    "faqs": (FAQ, FAQForm, "FAQs"),
    "testimonials": (Testimonial, TestimonialForm, "Testimonials"),
    "blogs": (Blog, BlogForm, "Blog posts"),
}


@role_required(User.Role.ADMIN, User.Role.PRODUCT_MANAGER)
def cms_list(request, kind):
    Model, Form, label = _CMS_MAP[kind]
    return render(request, "dashboard/cms_list.html", {
        "items": Model.objects.all(), "kind": kind, "label": label,
        "section": "cms",
    })


@role_required(User.Role.ADMIN, User.Role.PRODUCT_MANAGER)
def cms_edit(request, kind, pk=None):
    Model, Form, label = _CMS_MAP[kind]
    obj = get_object_or_404(Model, pk=pk) if pk else None
    form = Form(request.POST or None, request.FILES or None, instance=obj)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, f"{label[:-1]} saved.")
        return redirect("dashboard:cms_list", kind=kind)
    return render(request, "dashboard/cms_form.html",
                  {"form": form, "kind": kind, "label": label, "section": "cms"})


@role_required(User.Role.ADMIN, User.Role.PRODUCT_MANAGER)
def cms_delete(request, kind, pk):
    Model, _, _ = _CMS_MAP[kind]
    Model.objects.filter(pk=pk).delete()
    messages.info(request, "Deleted.")
    return redirect("dashboard:cms_list", kind=kind)


# --- Custom design review -------------------------------------------------
@staff_required
def designs(request):
    qs = CustomDesign.objects.select_related("product", "user")
    if request.method == "POST":
        d = get_object_or_404(CustomDesign, pk=request.POST.get("id"))
        d.status = request.POST.get("status", d.status)
        d.admin_note = request.POST.get("admin_note", "")
        d.save(update_fields=["status", "admin_note"])
        messages.success(request, "Design reviewed.")
        return redirect("dashboard:designs")
    return render(request, "dashboard/designs.html", {
        "designs": qs[:100], "statuses": CustomDesign.Status.choices, "section": "designs",
    })


# --- Reports (CSV export) -------------------------------------------------
@role_required(User.Role.ADMIN)
def reports(request):
    return render(request, "dashboard/reports.html", {
        "messages_count": ContactMessage.objects.filter(handled=False).count(),
        "section": "reports",
    })


@role_required(User.Role.ADMIN)
def report_export(request, kind):
    resp = HttpResponse(content_type="text/csv")
    resp["Content-Disposition"] = f'attachment; filename="{kind}_report.csv"'
    w = csv.writer(resp)
    if kind == "sales":
        w.writerow(["Order No", "Date", "Customer", "Status", "Payment", "Total"])
        for o in Order.objects.all():
            w.writerow([o.order_no, o.created_at.date(), o.full_name, o.status,
                        o.payment_status, o.total])
    elif kind == "gst":
        w.writerow(["Invoice", "Order", "GSTIN", "Taxable", "GST", "Total"])
        for o in Order.objects.filter(payment_status=Order.Payment.PAID):
            w.writerow([getattr(getattr(o, "invoice", None), "invoice_no", ""), o.order_no,
                        o.gst_number, o.subtotal - o.discount, o.gst, o.total])
    elif kind == "products":
        w.writerow(["Product", "Category", "Price", "Sold", "Views"])
        for p in Product.objects.select_related("category"):
            w.writerow([p.name, p.category.name, p.base_price, p.sold_count, p.view_count])
    elif kind == "customers":
        w.writerow(["Name", "Email", "Phone", "Orders", "Joined"])
        for u in User.objects.filter(role__in=[User.Role.CUSTOMER, User.Role.CORPORATE]) \
                .annotate(oc=Count("orders")):
            w.writerow([u.get_full_name(), u.email, u.phone, u.oc, u.created_at.date()])
    return resp


# --- Audit log ------------------------------------------------------------
@role_required(User.Role.ADMIN)
def audit(request):
    return render(request, "dashboard/audit.html", {
        "logs": AuditLog.objects.select_related("user")[:200],
        "notifications": Notification.objects.all()[:50],
        "section": "audit",
    })
