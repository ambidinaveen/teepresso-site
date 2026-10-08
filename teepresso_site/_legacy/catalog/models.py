from django.db import models


class Quality(models.Model):
    """T-shirt quality / GSM grade (REQ-CW-4)."""

    name = models.CharField(max_length=60)          # e.g. "180 GSM – Premium"
    gsm = models.IntegerField()
    price_delta = models.IntegerField(
        default=0, help_text="₹ added to the per-piece tier price"
    )
    sort = models.IntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort", "gsm"]
        verbose_name_plural = "Qualities"

    def __str__(self):
        return self.name


class Color(models.Model):
    name = models.CharField(max_length=40)
    hex = models.CharField(max_length=7, default="#000000")
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class Size(models.Model):
    code = models.CharField(max_length=8)           # S, M, L, XL, XXL
    sort = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort"]

    def __str__(self):
        return self.code


class Product(models.Model):
    """A T-shirt type (REQ-CW-5)."""

    name = models.CharField(max_length=80)          # Round Neck, Polo, ...
    description = models.CharField(max_length=200, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class PricingTier(models.Model):
    """Quantity-slab pricing (REQ-CW-9). Admin-editable (REQ-CW-11).

    A tier applies when ordered quantity >= min_qty. The highest matching
    tier wins.  Placeholder values are seeded; replace with the real price list.
    """

    min_qty = models.IntegerField(unique=True)
    unit_price = models.IntegerField(help_text="₹ per piece at or above min_qty")

    class Meta:
        ordering = ["min_qty"]

    def __str__(self):
        return f"≥{self.min_qty} pcs → ₹{self.unit_price}/pc"
