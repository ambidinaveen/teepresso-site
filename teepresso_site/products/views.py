from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from core.ai import recommend, track_view

from .models import Brand, Category, CustomDesign, Product, Review


def product_list(request):
    qs = Product.objects.filter(active=True).select_related("category", "brand")

    cat_slug = request.GET.get("category")
    if cat_slug:
        qs = qs.filter(Q(category__slug=cat_slug) | Q(category__parent__slug=cat_slug))
    brand_slug = request.GET.get("brand")
    if brand_slug:
        qs = qs.filter(brand__slug=brand_slug)

    q = request.GET.get("q", "").strip()
    if q:
        qs = qs.filter(Q(name__icontains=q) | Q(short_description__icontains=q) |
                       Q(category__name__icontains=q))

    pmin, pmax = request.GET.get("min"), request.GET.get("max")
    if pmin and pmin.isdigit():
        qs = qs.filter(base_price__gte=int(pmin))
    if pmax and pmax.isdigit():
        qs = qs.filter(base_price__lte=int(pmax))

    sort = request.GET.get("sort", "popular")
    qs = {
        "popular": qs.order_by("-sold_count", "-view_count"),
        "new": qs.order_by("-created_at"),
        "price_low": qs.order_by("base_price"),
        "price_high": qs.order_by("-base_price"),
    }.get(sort, qs.order_by("-sold_count"))

    page = Paginator(qs, 12).get_page(request.GET.get("page"))
    ctx = {
        "products": page,
        "categories": Category.objects.filter(active=True),
        "brands": Brand.objects.filter(active=True),
        "active_category": cat_slug,
        "q": q,
        "sort": sort,
        "total": page.paginator.count,
    }
    return render(request, "store/products.html", ctx)


def live_search(request):
    """AJAX live search dropdown (PRINTPROX: AJAX Live Search)."""
    q = request.GET.get("q", "").strip()
    results = []
    if len(q) >= 2:
        for p in Product.objects.filter(active=True).filter(
            Q(name__icontains=q) | Q(category__name__icontains=q)
        )[:8]:
            results.append({
                "name": p.name,
                "url": p.get_absolute_url(),
                "price": float(p.price),
                "image": p.image.url if p.image else "",
                "category": p.category.name,
            })
    return JsonResponse({"results": results})


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related("category", "brand")
        .prefetch_related("images", "videos", "variants", "reviews"),
        slug=slug, active=True,
    )
    Product.objects.filter(pk=product.pk).update(view_count=product.view_count + 1)
    track_view(request, product.id)

    variant_groups = {}
    for v in product.variants.all():
        variant_groups.setdefault(v.name, []).append(v)

    ctx = {
        "product": product,
        "variant_groups": variant_groups,
        "reviews": product.reviews.filter(approved=True),
        "related": recommend(request, limit=4, exclude_ids=[product.id]),
        "in_wishlist": request.user.is_authenticated and
        request.user.wishlist_items.filter(product=product).exists(),
    }
    return render(request, "store/product_detail.html", ctx)


def add_review(request, slug):
    product = get_object_or_404(Product, slug=slug, active=True)
    if request.method == "POST":
        rating = int(request.POST.get("rating", 5) or 5)
        comment = (request.POST.get("comment") or "").strip()
        name = request.user.display_name if request.user.is_authenticated \
            else (request.POST.get("name") or "Anonymous")
        Review.objects.create(
            product=product, user=request.user if request.user.is_authenticated else None,
            name=name, rating=max(1, min(5, rating)), comment=comment,
        )
        messages.success(request, "Thanks for your review!")
    return redirect(product.get_absolute_url())


def customize(request, slug):
    """Customization studio: upload logo/text, position with Fabric.js, preview."""
    product = get_object_or_404(Product, slug=slug, active=True, is_customizable=True)
    if request.method == "POST":
        design = CustomDesign.objects.create(
            product=product,
            user=request.user if request.user.is_authenticated else None,
            logo=request.FILES.get("logo"),
            custom_text=request.POST.get("custom_text", "")[:200],
            font=request.POST.get("font", ""),
            font_size=int(request.POST.get("font_size", 24) or 24),
            text_color=request.POST.get("text_color", "#000000"),
            print_position=request.POST.get("print_position", "Front Center"),
            design_json=request.POST.get("design_json", ""),
            preview=request.POST.get("preview", ""),
            status=CustomDesign.Status.PENDING,
        )
        request.session["last_design_id"] = design.id
        messages.success(request, "Your design has been saved and submitted for review.")
        from cart.utils import get_cart
        cart = get_cart(request)
        cart.add(product, qty=product.min_order_qty, design=design)
        return redirect("cart:detail")
    return render(request, "store/customize.html", {"product": product})


@login_required
def my_designs(request):
    designs = CustomDesign.objects.filter(user=request.user).select_related("product")
    return render(request, "account/designs.html", {"designs": designs})
