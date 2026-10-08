from django.contrib import messages
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from core.ai import chatbot_reply

from .models import FAQ, ContactMessage, Newsletter, Page


def faq(request):
    faqs = FAQ.objects.filter(active=True)
    cats = sorted(set(f.category for f in faqs))
    return render(request, "cms/faq.html", {"faqs": faqs, "categories": cats})


def page(request, slug):
    obj = get_object_or_404(Page, slug=slug, active=True)
    return render(request, "cms/page.html", {"page": obj})


def contact(request):
    if request.method == "POST":
        ContactMessage.objects.create(
            name=request.POST.get("name", "")[:120],
            email=request.POST.get("email", ""),
            phone=request.POST.get("phone", "")[:20],
            subject=request.POST.get("subject", "")[:160],
            message=request.POST.get("message", ""),
        )
        messages.success(request, "Thanks! We'll get back to you shortly.")
        return redirect("cms:contact")
    return render(request, "cms/contact.html")


def newsletter_subscribe(request):
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip()
        if email:
            Newsletter.objects.get_or_create(email=email)
            if request.headers.get("x-requested-with") == "XMLHttpRequest":
                return JsonResponse({"ok": True, "message": "Subscribed! 🎉"})
            messages.success(request, "Subscribed to our newsletter! 🎉")
    return redirect(request.META.get("HTTP_REFERER", "storefront:index"))


def chatbot(request):
    """AI support chatbot endpoint (rule-based)."""
    text = request.GET.get("q", "") or request.POST.get("q", "")
    return JsonResponse({"reply": chatbot_reply(text)})
