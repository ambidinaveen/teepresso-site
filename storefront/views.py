from django.shortcuts import render

from blogs.models import Blog
from cms.models import Banner, FAQ, Testimonial
from core.ai import recommend
from products.models import Category, Product


def index(request):
    products = Product.objects.filter(active=True)
    ctx = {
        "banners": Banner.objects.filter(active=True),
        "categories": Category.objects.filter(active=True, parent__isnull=True)[:6],
        "featured": products.filter(featured=True)[:8],
        "trending": products.filter(trending=True)[:8],
        "best_sellers": products.filter(best_seller=True).order_by("-sold_count")[:8],
        "recommended": recommend(request, limit=4),
        "testimonials": Testimonial.objects.filter(active=True)[:6],
        "faqs": FAQ.objects.filter(active=True)[:6],
        "posts": Blog.objects.filter(published=True)[:3],
    }
    return render(request, "store/index.html", ctx)
