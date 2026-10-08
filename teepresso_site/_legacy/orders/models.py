from django.conf import settings
from django.db import models
from django.utils.crypto import get_random_string

from accounts.models import Customer, User
from catalog.models import Product, Quality, Color, Size


class Order(models.Model):
    """One configured design (product+quality+colour), many sizes (REQ-CW-6/8)."""

    class Status(models.TextChoices):
        NEW = "new", "New"
        DESIGN = "design", "In Design"
        PRODUCTION = "production", "In Production"
        QC = "qc", "Quality Check"
        DISPATCHED = "dispatched", "Dispatched"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    class Channel(models.TextChoices):
        ONLINE = "online", "Online"
        OFFLINE = "offline", "Offline"

    class Payment(models.TextChoices):
        # 'enquiry' = order taken but online payment not yet collected (safe mode)
        ENQUIRY = "enquiry", "Enquiry (unpaid)"
        UNPAID = "unpaid", "Unpaid"
        PAID = "paid", "Paid"
        REFUNDED = "refunded", "Refunded"

    order_no = models.CharField(max_length=20, unique=True, blank=True)
    customer = models.ForeignKey(Customer, on_delete=models.PROTECT, related_name="orders")
    channel = models.CharField(max_length=10, choices=Channel.choices, default=Channel.ONLINE)

    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quality = models.ForeignKey(Quality, on_delete=models.PROTECT)
    color = models.ForeignKey(Color, on_delete=models.PROTECT)

    urgent = models.BooleanField(default=False)
    qty_total = models.IntegerField(default=0)
    subtotal = models.IntegerField(default=0)
    urgent_charge = models.IntegerField(default=0)
    gst = models.IntegerField(default=0)
    total = models.IntegerField(default=0)

    status = models.CharField(max_length=20, choices=Status.choices, default=Status.NEW)
    payment_status = models.CharField(
        max_length=10, choices=Payment.choices, default=Payment.ENQUIRY
    )
    wants_mockup = models.BooleanField(default=False)
    address = models.TextField(blank=True)
    # Customer's own design arrangement (REQ-CW-12):
    #  design_json   = structured list of text items {text,x%,y%,size,color,bold,font}
    #  design_preview= rendered PNG (data URL) so staff/admin see the exact layout
    design_json = models.TextField(blank=True)
    design_preview = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if not self.order_no:
            self.order_no = "TP-" + get_random_string(6, "0123456789")
        super().save(*args, **kwargs)

    def __str__(self):
        return self.order_no

    # --- business-rule helpers (single source of truth) ---
    @property
    def is_bulk(self):
        return self.qty_total > settings.TEEPRESSO["BULK_FOLLOWUP_QTY"]

    @property
    def needs_eway(self):
        return self.total > settings.TEEPRESSO["EWAY_THRESHOLD"]

    @property
    def design_summary(self):
        return f"{self.product.name} · {self.quality.name} · {self.color.name}"

    def apply_quote(self, q):
        self.qty_total = q["qty"]
        self.subtotal = q["subtotal"]
        self.urgent_charge = q["urgent_charge"]
        self.gst = q["gst"]
        self.total = q["total"]


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    size = models.ForeignKey(Size, on_delete=models.PROTECT)
    qty = models.IntegerField(default=0)
    unit_price = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.size.code}×{self.qty}"


class OrderStatusEvent(models.Model):
    """Auditable status history — powers customer tracking + internal screens (REQ-TRK)."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="events")
    status = models.CharField(max_length=20)
    note = models.CharField(max_length=200, blank=True)
    actor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    ts = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["ts"]


class Mockup(models.Model):
    """Teepresso/customer mockup with watermark-until-approval (REQ-EDT-5)."""

    class Approval(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved"
        DECLINED = "declined", "Revision asked"

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="mockups")
    kind = models.CharField(max_length=20, default="teepresso")  # teepresso | customer
    title = models.CharField(max_length=120, blank=True)
    watermarked = models.BooleanField(default=True)
    approval_status = models.CharField(
        max_length=20, choices=Approval.choices, default=Approval.PENDING
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def approve(self):
        self.approval_status = self.Approval.APPROVED
        self.watermarked = False  # clean files released on approval (BR-5)
        self.save(update_fields=["approval_status", "watermarked"])


class PaymentRecord(models.Model):
    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="payment")
    method = models.CharField(max_length=20, default="upi")
    status = models.CharField(max_length=20, default="unpaid")
    amount = models.IntegerField(default=0)
    reference = models.CharField(max_length=80, blank=True)
    ts = models.DateTimeField(auto_now_add=True)


class Shipment(models.Model):
    """Dispatch & shipping (REQ-DSP)."""

    class QC(models.TextChoices):
        PENDING = "pending", "Pending"
        PASS = "pass", "Passed"
        FAIL = "fail", "Failed"

    order = models.OneToOneField(Order, on_delete=models.CASCADE, related_name="shipment")
    piece_count_verified = models.IntegerField(null=True, blank=True)
    qc_result = models.CharField(max_length=10, choices=QC.choices, default=QC.PENDING)
    qc_reprinted = models.IntegerField(default=0)
    invoice_no = models.CharField(max_length=40, blank=True)
    awb = models.CharField(max_length=40, blank=True)
    courier = models.CharField(max_length=60, blank=True)
    # E-Way: flagged when required; number stays blank until really filed (safe)
    eway_required = models.BooleanField(default=False)
    eway_no = models.CharField(max_length=40, blank=True)
    dispatched = models.BooleanField(default=False)
    ts = models.DateTimeField(auto_now_add=True)
