from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils.crypto import get_random_string


class Order(models.Model):
    """A placed order. Workflow: Pending → Confirmed → Processing → Printing →
    Packaging → Shipped → Delivered (PRINTPROX order workflow)."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        CONFIRMED = "confirmed", "Confirmed"
        PROCESSING = "processing", "Processing"
        PRINTING = "printing", "Printing"
        PACKAGING = "packaging", "Packaging"
        SHIPPED = "shipped", "Shipped"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class Payment(models.TextChoices):
        ENQUIRY = "enquiry", "Enquiry (unpaid)"
        PENDING = "pending", "Payment pending"
        PAID = "paid", "Paid"
        REFUNDED = "refunded", "Refunded"
        FAILED = "failed", "Failed"

    WORKFLOW = [Status.PENDING, Status.CONFIRMED, Status.PROCESSING, Status.PRINTING,
                Status.PACKAGING, Status.SHIPPED, Status.DELIVERED]

    order_no = models.CharField(max_length=20, unique=True, blank=True)
    user = models.ForeignKey(
        "accounts.User", null=True, blank=True, on_delete=models.SET_NULL,
        related_name="orders",
    )
    # snapshot of customer + delivery details
    full_name = models.CharField(max_length=120)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20)
    company = models.CharField(max_length=160, blank=True)
    gst_number = models.CharField(max_length=20, blank=True)
    billing_address = models.TextField(blank=True)
    shipping_address = models.TextField()

    # money
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    gst = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    shipping = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    coupon_code = models.CharField(max_length=30, blank=True)

    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    payment_status = models.CharField(max_length=10, choices=Payment.choices,
                                      default=Payment.ENQUIRY)
    payment_method = models.CharField(max_length=20, default="razorpay")
    tracking_number = models.CharField(max_length=60, blank=True)
    courier = models.CharField(max_length=80, blank=True)
    notes = models.CharField(max_length=300, blank=True)
    eway_required = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.order_no:
            self.order_no = "TP" + get_random_string(8, "0123456789")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.order_no

    @property
    def qty_total(self):
        return sum(i.qty for i in self.items.all())

    @property
    def is_bulk(self):
        return self.qty_total > settings.TEEPRESSO["BULK_FOLLOWUP_QTY"]

    @property
    def needs_eway(self):
        return self.total > settings.TEEPRESSO["EWAY_THRESHOLD"]

    @property
    def status_label(self):
        return self.Status(self.status).label

    def set_status(self, new_status, actor=None, note=""):
        self.status = new_status
        self.save(update_fields=["status"])
        OrderStatusEvent.objects.create(order=self, status=new_status, actor=actor, note=note)

    def timeline(self):
        labels = dict(self.Status.choices)
        if self.status == self.Status.CANCELLED:
            return [{"label": "Cancelled", "active": True, "done": False}]
        idx = self.WORKFLOW.index(self.Status(self.status)) if self.status in \
            [s.value for s in self.WORKFLOW] else 0
        out = []
        for i, st in enumerate(self.WORKFLOW):
            out.append({"label": labels[st], "done": i < idx, "active": i == idx})
        return out


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.PROTECT)
    design = models.ForeignKey(
        "products.CustomDesign", null=True, blank=True, on_delete=models.SET_NULL
    )
    name = models.CharField(max_length=160)
    variant_label = models.CharField(max_length=120, blank=True)
    qty = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))

    @property
    def line_total(self):
        return (self.unit_price * self.qty).quantize(Decimal("0.01"))


class OrderStatusEvent(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="events")
    status = models.CharField(max_length=20)
    note = models.CharField(max_length=240, blank=True)
    actor = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]


class Invoice(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="invoice")
    invoice_no = models.CharField(max_length=30, unique=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.invoice_no:
            self.invoice_no = "INV-" + get_random_string(8, "0123456789")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.invoice_no
