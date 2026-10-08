from decimal import Decimal

from django.db import models
from django.utils import timezone

from products.pricing import unit_price_for_qty


class Coupon(models.Model):
    class Kind(models.TextChoices):
        PERCENT = "percent", "Percent off"
        FLAT = "flat", "Flat amount off"

    code = models.CharField(max_length=30, unique=True)
    kind = models.CharField(max_length=10, choices=Kind.choices, default=Kind.PERCENT)
    value = models.DecimalField(max_digits=10, decimal_places=2)
    min_order = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    description = models.CharField(max_length=160, blank=True)
    active = models.BooleanField(default=True)
    expires = models.DateField(null=True, blank=True)
    used_count = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.code

    def is_valid(self, subtotal):
        if not self.active:
            return False, "This coupon is not active."
        if self.expires and self.expires < timezone.localdate():
            return False, "This coupon has expired."
        if subtotal < self.min_order:
            return False, f"Add items worth ₹{self.min_order:.0f} to use this coupon."
        return True, ""

    def discount_for(self, subtotal):
        subtotal = Decimal(str(subtotal))
        if self.kind == self.Kind.PERCENT:
            return (subtotal * self.value / Decimal(100)).quantize(Decimal("0.01"))
        return min(self.value, subtotal)


class Cart(models.Model):
    user = models.OneToOneField(
        "accounts.User", null=True, blank=True, on_delete=models.CASCADE, related_name="cart"
    )
    session_key = models.CharField(max_length=40, blank=True, db_index=True)
    coupon = models.ForeignKey(Coupon, null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Cart #{self.pk}"

    def add(self, product, qty=1, variant_label="", variant_delta=0, design=None):
        item = self.items.filter(product=product, variant_label=variant_label,
                                 design=design).first()
        if item:
            item.qty += int(qty)
            item.save(update_fields=["qty"])
        else:
            item = self.items.create(
                product=product, qty=int(qty), variant_label=variant_label,
                variant_delta=Decimal(str(variant_delta or 0)), design=design,
            )
        return item

    @property
    def item_count(self):
        return sum(i.qty for i in self.items.all())

    @property
    def subtotal(self):
        return sum((i.line_total for i in self.items.all()), Decimal("0"))

    @property
    def discount(self):
        if self.coupon:
            ok, _ = self.coupon.is_valid(self.subtotal)
            if ok:
                return self.coupon.discount_for(self.subtotal)
        return Decimal("0")

    @property
    def taxable(self):
        return max(self.subtotal - self.discount, Decimal("0"))

    @property
    def gst(self):
        from django.conf import settings
        rate = Decimal(str(settings.TEEPRESSO["GST_RATE"]))
        return (self.taxable * rate / Decimal(100)).quantize(Decimal("0.01"))

    @property
    def shipping(self):
        from django.conf import settings
        rules = settings.TEEPRESSO
        if self.subtotal == 0 or self.subtotal >= rules["FREE_SHIP_OVER"]:
            return Decimal("0")
        return Decimal(str(rules["SHIP_FLAT"]))

    @property
    def total(self):
        return (self.taxable + self.gst + self.shipping).quantize(Decimal("0.01"))


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE)
    variant_label = models.CharField(max_length=120, blank=True)
    variant_delta = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))
    design = models.ForeignKey(
        "products.CustomDesign", null=True, blank=True, on_delete=models.SET_NULL
    )
    qty = models.PositiveIntegerField(default=1)
    saved_for_later = models.BooleanField(default=False)
    added_at = models.DateTimeField(auto_now_add=True)

    @property
    def unit_price(self):
        return unit_price_for_qty(self.product.price + self.variant_delta, self.qty)

    @property
    def line_total(self):
        return (self.unit_price * self.qty).quantize(Decimal("0.01"))
