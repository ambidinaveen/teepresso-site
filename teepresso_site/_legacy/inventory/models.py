from django.db import models

from accounts.models import User
from catalog.models import Product, Quality, Color, Size


class StockItem(models.Model):
    """Stock keyed by SKU = quality × type × colour × size (REQ-INV-1)."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quality = models.ForeignKey(Quality, on_delete=models.CASCADE)
    color = models.ForeignKey(Color, on_delete=models.CASCADE)
    size = models.ForeignKey(Size, on_delete=models.CASCADE)
    in_stock = models.IntegerField(default=0)
    reorder_level = models.IntegerField(default=100)

    class Meta:
        unique_together = ("product", "quality", "color", "size")

    @property
    def sku(self):
        return (
            f"{self.quality.gsm}-{self.product.name[:3].upper()}-"
            f"{self.color.name[:3].upper()}-{self.size.code}"
        )

    @property
    def status(self):
        if self.in_stock <= 0:
            return "out"
        if self.in_stock <= self.reorder_level:
            return "low"
        return "in"

    def __str__(self):
        return self.sku


class StockMovement(models.Model):
    """Auditable stock in/out (REQ-INV-2)."""

    class Kind(models.TextChoices):
        IN = "in", "Stock In"
        OUT = "out", "Stock Out"

    item = models.ForeignKey(StockItem, on_delete=models.CASCADE, related_name="movements")
    kind = models.CharField(max_length=4, choices=Kind.choices)
    qty = models.IntegerField()
    by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL)
    note = models.CharField(max_length=120, blank=True)
    ts = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-ts"]

    def apply(self):
        """Adjust the item's stock and persist the movement atomically-ish."""
        if self.kind == self.Kind.IN:
            self.item.in_stock += self.qty
        else:
            self.item.in_stock = max(0, self.item.in_stock - self.qty)
        self.item.save(update_fields=["in_stock"])
        self.save()
