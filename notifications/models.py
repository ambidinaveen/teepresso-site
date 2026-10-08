from django.db import models


class Notification(models.Model):
    class Channel(models.TextChoices):
        EMAIL = "email", "Email"
        WHATSAPP = "whatsapp", "WhatsApp"
        SMS = "sms", "SMS"

    class Status(models.TextChoices):
        SENT = "sent", "Sent"
        QUEUED = "queued", "Queued (safe mode)"
        FAILED = "failed", "Failed"

    channel = models.CharField(max_length=10, choices=Channel.choices)
    event = models.CharField(max_length=40)
    recipient = models.CharField(max_length=160)
    subject = models.CharField(max_length=200, blank=True)
    body = models.TextField(blank=True)
    link = models.URLField(blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED)
    order = models.ForeignKey(
        "orders.Order", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="notifications",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.channel} → {self.recipient} ({self.event})"
