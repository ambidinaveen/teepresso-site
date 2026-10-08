from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from .models import Blog, BlogCategory


def blog_list(request):
    qs = Blog.objects.filter(published=True).select_related("category")
    cat = request.GET.get("category")
    if cat:
        qs = qs.filter(category__slug=cat)
    page = Paginator(qs, 9).get_page(request.GET.get("page"))
    return render(request, "blogs/list.html", {
        "posts": page, "categories": BlogCategory.objects.all(), "active_category": cat,
    })


def blog_detail(request, slug):
    post = get_object_or_404(Blog, slug=slug, published=True)
    related = Blog.objects.filter(published=True, category=post.category).exclude(pk=post.pk)[:3]
    return render(request, "blogs/detail.html", {"post": post, "related": related})
