from django.db import models

from orders.models import Order


class WhatsAppMessage(models.Model):
    """A WhatsApp message (e.g. the bill) sent — or queued to send — to a customer.

    status:
      queued = built & ready; in safe mode staff send it with one click (no ban risk)
      sent   = delivered via the official WhatsApp Business API
      failed = API attempt failed (kept for retry)
    """

    class Kind(models.TextChoices):
        BILL = "bill", "Bill / Invoice"
        MOCKUP = "mockup", "Mockup"
        STATUS = "status", "Status update"

    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        SENT = "sent", "Sent"
        FAILED = "failed", "Failed"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="messages")
    phone = models.CharField(max_length=20)
    kind = models.CharField(max_length=12, choices=Kind.choices, default=Kind.BILL)
    body = models.TextField()
    link = models.TextField(blank=True)        # bill URL referenced in the message
    wa_link = models.TextField(blank=True)     # one-click wa.me link (safe manual send)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.get_kind_display()} → {self.phone} ({self.status})"
