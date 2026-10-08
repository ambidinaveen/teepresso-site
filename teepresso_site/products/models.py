from decimal import Decimal

from django.db import models
from django.db.models import Avg
from django.urls import reverse
from django.utils.text import slugify


class Category(models.Model):
    """Product category; self-referential for the mega-menu (parent -> children)."""

    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=90, unique=True, blank=True)
    parent = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.CASCADE, related_name="children"
    )
    icon = models.CharField(max_length=40, blank=True, help_text="Bootstrap icon name, e.g. 'gift'")
    image = models.ImageField(upload_to="categories/", blank=True, null=True)
    description = models.CharField(max_length=240, blank=True)
    sort = models.IntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort", "name"]
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:90]
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("products:list") + f"?category={self.slug}"


class Brand(models.Model):
    name = models.CharField(max_length=80)
    slug = models.SlugField(max_length=90, unique=True, blank=True)
    active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)[:90]
        super().save(*args, **kwargs)


class Product(models.Model):
    name = models.CharField(max_length=160)
    slug = models.SlugField(max_length=180, unique=True, blank=True)
    sku = models.CharField(max_length=40, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    brand = models.ForeignKey(Brand, null=True, blank=True, on_delete=models.SET_NULL)

    short_description = models.CharField(max_length=240, blank=True)
    description = models.TextField(blank=True)
    specifications = models.TextField(
        blank=True, help_text="One 'Key: Value' per line; rendered as a spec table."
    )

    image = models.ImageField(upload_to="products/", blank=True, null=True)
    base_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0"))
    sale_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True,
        help_text="If set and lower than base price, shown as the discounted price.",
    )
    min_order_qty = models.PositiveIntegerField(default=1)

    is_customizable = models.BooleanField(default=True)
    featured = models.BooleanField(default=False)
    trending = models.BooleanField(default=False)
    best_seller = models.BooleanField(default=False)
    active = models.BooleanField(default=True)

    sold_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.name)[:170] or "product"
            slug, i = base, 1
            while Product.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                i += 1
                slug = f"{base}-{i}"
            self.slug = slug
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("products:detail", args=[self.slug])

    # --- pricing helpers ---
    @property
    def price(self):
        if self.sale_price and self.sale_price < self.base_price:
            return self.sale_price
        return self.base_price

    @property
    def on_sale(self):
        return bool(self.sale_price and self.sale_price < self.base_price)

    @property
    def discount_pct(self):
        if self.on_sale and self.base_price:
            return int(round((1 - self.sale_price / self.base_price) * 100))
        return 0

    # --- review/rating helpers ---
    @property
    def avg_rating(self):
        return self.reviews.filter(approved=True).aggregate(a=Avg("rating"))["a"] or 0

    @property
    def review_count(self):
        return self.reviews.filter(approved=True).count()

    @property
    def stars(self):
        return range(int(round(self.avg_rating)))

    # --- stock ---
    @property
    def in_stock(self):
        inv = getattr(self, "inventory", None)
        return inv.quantity > 0 if inv else True

    @property
    def low_stock(self):
        inv = getattr(self, "inventory", None)
        return bool(inv and inv.quantity <= inv.low_stock_threshold)

    @property
    def spec_rows(self):
        rows = []
        for line in self.specifications.splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                rows.append((k.strip(), v.strip()))
        return rows


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/gallery/")
    alt = models.CharField(max_length=160, blank=True)
    sort = models.IntegerField(default=0)

    class Meta:
        ordering = ["sort", "id"]


class ProductVideo(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="videos")
    url = models.URLField(help_text="YouTube/Vimeo embed or direct URL")
    title = models.CharField(max_length=160, blank=True)


class ProductVariant(models.Model):
    """Selectable option, e.g. Size=L / Color=Navy, with optional price delta + stock."""

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="variants")
    name = models.CharField(max_length=40, help_text="e.g. 'Size', 'Color'")
    value = models.CharField(max_length=60, help_text="e.g. 'L', 'Navy Blue'")
    price_delta = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0"))
    stock = models.PositiveIntegerField(default=0)
    sort = models.IntegerField(default=0)

    class Meta:
        ordering = ["name", "sort", "value"]

    def __str__(self):
        return f"{self.name}: {self.value}"


class Inventory(models.Model):
    product = models.OneToOneField(Product, on_delete=models.CASCADE, related_name="inventory")
    quantity = models.IntegerField(default=0)
    low_stock_threshold = models.IntegerField(default=10)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Inventory"

    def __str__(self):
        return f"{self.product.name}: {self.quantity} in stock"


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(max_length=120)
    rating = models.PositiveSmallIntegerField(default=5)
    comment = models.TextField(blank=True)
    approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.product.name} · {self.rating}★"


class CustomDesign(models.Model):
    """A customer's product personalisation (logo/text/position) + admin review.

    `design_json` holds the Fabric.js canvas state; `preview` holds a rendered
    PNG data-URL so staff/admin can see the exact layout (PRINTPROX customization).
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        PENDING = "pending", "Pending review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        CHANGES = "changes", "Changes requested"

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="designs")
    user = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL)
    logo = models.ImageField(upload_to="designs/logos/", blank=True, null=True)
    custom_text = models.CharField(max_length=200, blank=True)
    font = models.CharField(max_length=60, blank=True)
    font_size = models.IntegerField(default=24)
    text_color = models.CharField(max_length=7, default="#000000")
    print_position = models.CharField(max_length=40, default="Front Center")
    design_json = models.TextField(blank=True)
    preview = models.TextField(blank=True)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.PENDING)
    admin_note = models.CharField(max_length=240, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Design #{self.pk} for {self.product.name}"
