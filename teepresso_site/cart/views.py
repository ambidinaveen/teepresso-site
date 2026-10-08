from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from products.models import Product

from .models import CartItem, Coupon
from .utils import get_cart


def _cart_payload(cart):
    return {
        "count": cart.item_count,
        "subtotal": float(cart.subtotal),
        "discount": float(cart.discount),
        "gst": float(cart.gst),
        "shipping": float(cart.shipping),
        "total": float(cart.total),
    }


def detail(request):
    cart = get_cart(request)
    items = cart.items.filter(saved_for_later=False).select_related("product", "design")
    saved = cart.items.filter(saved_for_later=True).select_related("product")
    return render(request, "store/cart.html", {"cart": cart, "items": items, "saved": saved})


def add(request, product_id):
    product = get_object_or_404(Product, pk=product_id, active=True)
    cart = get_cart(request)
    qty = max(int(request.POST.get("qty", product.min_order_qty) or 1), 1)

    labels, delta = [], 0
    for v in product.variants.all():
        chosen = request.POST.get(f"variant_{v.name}")
        if chosen == v.value:
            labels.append(f"{v.name}: {v.value}")
            delta += float(v.price_delta)
    cart.add(product, qty=qty, variant_label=", ".join(labels), variant_delta=delta)

    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, **_cart_payload(cart),
                             "message": f"Added {product.name} to cart."})
    messages.success(request, f"Added {product.name} to your cart.")
    return redirect("cart:detail")


def update(request, item_id):
    cart = get_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    qty = int(request.POST.get("qty", 1) or 1)
    if qty <= 0:
        item.delete()
    else:
        item.qty = qty
        item.save(update_fields=["qty"])
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        line = item.line_total if qty > 0 else 0
        return JsonResponse({"ok": True, "line_total": float(line), **_cart_payload(cart)})
    return redirect("cart:detail")


def remove(request, item_id):
    cart = get_cart(request)
    CartItem.objects.filter(pk=item_id, cart=cart).delete()
    if request.headers.get("x-requested-with") == "XMLHttpRequest":
        return JsonResponse({"ok": True, **_cart_payload(cart)})
    messages.info(request, "Item removed.")
    return redirect("cart:detail")


def save_for_later(request, item_id):
    cart = get_cart(request)
    item = get_object_or_404(CartItem, pk=item_id, cart=cart)
    item.saved_for_later = not item.saved_for_later
    item.save(update_fields=["saved_for_later"])
    return redirect("cart:detail")


def apply_coupon(request):
    cart = get_cart(request)
    code = (request.POST.get("code") or "").strip().upper()
    coupon = Coupon.objects.filter(code__iexact=code).first()
    if not coupon:
        messages.error(request, "Invalid coupon code.")
    else:
        ok, why = coupon.is_valid(cart.subtotal)
        if ok:
            cart.coupon = coupon
            cart.save(update_fields=["coupon"])
            messages.success(request, f"Coupon {coupon.code} applied!")
        else:
            messages.error(request, why)
    return redirect("cart:detail")


def remove_coupon(request):
    cart = get_cart(request)
    cart.coupon = None
    cart.save(update_fields=["coupon"])
    return redirect("cart:detail")
