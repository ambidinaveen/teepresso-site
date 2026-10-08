from django.contrib import messages
from django.shortcuts import redirect, render

from notifications.service import notify

from .forms import QuotationForm


def request_quote(request):
    form = QuotationForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        lead = form.save()
        notify("quotation", extra={"name": lead.contact_person},
               request=request)
        # email/whatsapp the lead's own contact + record
        from notifications.models import Notification
        Notification.objects.create(
            channel=Notification.Channel.EMAIL, event="quotation",
            recipient=lead.email, subject="We received your quotation request",
            body=f"Hi {lead.contact_person}, thanks for your bulk enquiry for "
                 f"{lead.quantity} pcs. Our corporate team will reach out soon.",
            status=Notification.Status.SENT,
        )
        messages.success(request, "Thank you! Our corporate team will contact you shortly.")
        return redirect("quotations:request")
    return render(request, "store/quotations.html", {"form": form})
