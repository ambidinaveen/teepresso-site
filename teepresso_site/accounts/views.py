from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from notifications.service import notify
from orders.models import Order

from .forms import AddressForm, LoginForm, ProfileForm, RegisterForm
from .models import OTP, Address

User = get_user_model()


def register(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    form = RegisterForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        otp = OTP.issue(user.email, OTP.Purpose.REGISTER)
        notify("register", user=user, otp=otp.code, request=request)
        login(request, user, backend="accounts.backends.EmailOrPhoneBackend")
        messages.success(request, f"Welcome to Teepresso, {user.display_name}! Your account is ready.")
        return redirect("accounts:dashboard")
    return render(request, "auth/register.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("accounts:dashboard")
    form = LoginForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = authenticate(
            request,
            username=form.cleaned_data["identifier"],
            password=form.cleaned_data["password"],
        )
        if user is None:
            messages.error(request, "Invalid credentials. Please try again.")
        elif user.is_blocked:
            messages.error(request, "This account has been blocked. Contact support.")
        else:
            login(request, user)
            messages.success(request, f"Welcome back, {user.display_name}!")
            nxt = request.GET.get("next")
            if nxt:
                return redirect(nxt)
            return redirect("dashboard:home" if user.is_staff_role else "accounts:dashboard")
    return render(request, "auth/login.html", {"form": form})


def logout_view(request):
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("storefront:index")


def forgot_password(request):
    """OTP-based reset. Safe mode: OTP shown on screen / printed (no real SMS)."""
    stage = "request"
    ident = ""
    if request.method == "POST":
        stage = request.POST.get("stage", "request")
        ident = (request.POST.get("identifier") or "").strip().lower()
        user = User.objects.filter(email__iexact=ident).first() or \
            User.objects.filter(phone=ident).first()
        if stage == "request":
            if user:
                otp = OTP.issue(user.email, OTP.Purpose.RESET)
                notify("password_reset", user=user, otp=otp.code, request=request)
                messages.info(request, "We sent you a reset code.")
                request.session["reset_ident"] = user.email
                return render(request, "auth/forgot.html",
                              {"stage": "verify", "ident": user.email,
                               "dev_otp": None if request.user.is_staff else otp.code})
            messages.error(request, "No account found with that email or mobile.")
        elif stage == "verify":
            email = request.session.get("reset_ident", ident)
            code = (request.POST.get("code") or "").strip()
            pw = request.POST.get("password") or ""
            otp = OTP.objects.filter(identifier=email, purpose=OTP.Purpose.RESET,
                                     used=False).order_by("-created_at").first()
            if otp and otp.code == code and otp.is_valid() and len(pw) >= 6:
                u = User.objects.get(email__iexact=email)
                u.set_password(pw)
                u.save()
                otp.used = True
                otp.save(update_fields=["used"])
                messages.success(request, "Password updated. Please log in.")
                return redirect("accounts:login")
            messages.error(request, "Invalid/expired code or password too short (min 6).")
            return render(request, "auth/forgot.html", {"stage": "verify", "ident": email})
    return render(request, "auth/forgot.html", {"stage": stage, "ident": ident})


# --- Customer account area -----------------------------------------------
@login_required
def dashboard(request):
    if request.user.is_staff_role:
        return redirect("dashboard:home")
    orders = Order.objects.filter(user=request.user)
    ctx = {
        "total_orders": orders.count(),
        "pending_orders": orders.exclude(
            status__in=[Order.Status.DELIVERED, Order.Status.CANCELLED]
        ).count(),
        "delivered_orders": orders.filter(status=Order.Status.DELIVERED).count(),
        "saved_designs": request.user.wishlist_items.count(),
        "recent_orders": orders[:5],
    }
    return render(request, "account/dashboard.html", ctx)


@login_required
def profile(request):
    form = ProfileForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Profile updated.")
        return redirect("accounts:profile")
    return render(request, "account/profile.html", {"form": form})


@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).prefetch_related("items")
    return render(request, "account/orders.html", {"orders": orders})


@login_required
def order_detail(request, order_no):
    order = get_object_or_404(Order, order_no=order_no, user=request.user)
    return render(request, "account/order_detail.html",
                  {"order": order, "timeline": order.timeline()})


@login_required
def addresses(request):
    form = AddressForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        addr = form.save(commit=False)
        addr.user = request.user
        addr.save()
        messages.success(request, "Address saved.")
        return redirect("accounts:addresses")
    return render(request, "account/addresses.html",
                  {"form": form, "addresses": request.user.addresses.all()})


@login_required
def address_delete(request, pk):
    Address.objects.filter(pk=pk, user=request.user).delete()
    messages.info(request, "Address removed.")
    return redirect("accounts:addresses")


# --- Wishlist -------------------------------------------------------------
@login_required
def wishlist(request):
    items = request.user.wishlist_items.select_related("product")
    return render(request, "account/wishlist.html", {"items": items})


@login_required
def wishlist_toggle(request, product_id):
    from django.http import JsonResponse
    from products.models import Product

    product = get_object_or_404(Product, pk=product_id)
    item = request.user.wishlist_items.filter(product=product).first()
    if item:
        item.delete()
        added = False
    else:
        request.user.wishlist_items.create(product=product)
        added = True
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, "added": added,
                             "count": request.user.wishlist_items.count()})
    messages.success(request, "Added to wishlist." if added else "Removed from wishlist.")
    return redirect(request.META.get("HTTP_REFERER", "accounts:wishlist"))
