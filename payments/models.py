from decimal import Decimal

from django.db import models


class Payment(models.Model):
    class Status(models.TextChoices):
        CREATED = "created", "Created"
        AWAITING = "awaiting", "Awaiting verification"
        PAID = "paid", "Paid"
        ENQUIRY = "enquiry", "Enquiry (pay later)"
        FAILED = "failed", "Failed"
        REFUNDED = "refunded", "Refunded"

    order = models.ForeignKey("orders.Order", on_delete=models.CASCADE, related_name="payments")
    method = models.CharField(max_length=20, default="razorpay")
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.CREATED)
    gateway_order_id = models.CharField(max_length=80, blank=True)
    gateway_payment_id = models.CharField(max_length=80, blank=True)
    # 12-digit UPI transaction reference (UTR) the customer enters after paying.
    # Used by staff to reconcile the payment against the bank/UPI statement.
    upi_ref = models.CharField(max_length=40, blank=True)
    note = models.CharField(max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.order.order_no} · {self.amount} · {self.status}"
