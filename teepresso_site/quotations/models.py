from django.db import models


class CorporateLead(models.Model):
    """Bulk / corporate gifting quotation request (PRINTPROX Corporate Bulk Order)."""

    class Status(models.TextChoices):
        NEW = "new", "New"
        CONTACTED = "contacted", "Contacted"
        PROPOSAL = "proposal", "Proposal sent"
        WON = "won", "Won"
        LOST = "lost", "Lost"

    company_name = models.CharField(max_length=160)
    contact_person = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    product_requirement = models.TextField()
    quantity = models.PositiveIntegerField(default=0)
    budget = models.CharField(max_length=60, blank=True)
    reference_file = models.FileField(upload_to="quotations/", blank=True, null=True)

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.NEW)
    assigned_to = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="assigned_leads",
    )
    followup_note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.company_name} ({self.quantity} pcs)"
