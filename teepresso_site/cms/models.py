from django.db import models
from django.utils.text import slugify


class Banner(models.Model):
    """Hero slider slide (PRINTPROX: Dynamic Banner Slider)."""

    title = models.CharField(max_length=140)
    subtitle = models.CharField(max_length=240, blank=True)
    image = models.ImageField(upload_to="banners/", blank=True, null=True)
    cta_text = models.CharField(max_length=40, default="Shop Now")
    cta_link = models.CharField(max_length=200, default="/products/")
    bg_gradient = models.CharField(
        max_length=120, blank=True,
        help_text="CSS gradient, e.g. 'linear-gradient(135deg,#6d28d9,#db2777)'",
    )
    sort = models.IntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort", "id"]

    def __str__(self):
        return self.title


class FAQ(models.Model):
    question = models.CharField(max_length=240)
    answer = models.TextField()
    category = models.CharField(max_length=60, default="General")
    sort = models.IntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort", "id"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self):
        return self.question


class Testimonial(models.Model):
    name = models.CharField(max_length=120)
    role = models.CharField(max_length=120, blank=True)
    avatar = models.ImageField(upload_to="testimonials/", blank=True, null=True)
    rating = models.PositiveSmallIntegerField(default=5)
    quote = models.TextField()
    is_corporate = models.BooleanField(default=False)
    sort = models.IntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["sort", "id"]

    def __str__(self):
        return self.name

    @property
    def stars(self):
        return range(self.rating)


class Page(models.Model):
    """CMS-managed static page (Terms, Privacy, About, etc.)."""

    title = models.CharField(max_length=140)
    slug = models.SlugField(max_length=160, unique=True, blank=True)
    body = models.TextField(help_text="HTML allowed.")
    active = models.BooleanField(default=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:160]
        super().save(*args, **kwargs)


class Newsletter(models.Model):
    email = models.EmailField(unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email


class ContactMessage(models.Model):
    name = models.CharField(max_length=120)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=160, blank=True)
    message = models.TextField()
    handled = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} — {self.subject or 'Contact'}"


class SiteSetting(models.Model):
    """Simple key/value site settings editable from the dashboard/admin."""

    key = models.CharField(max_length=60, unique=True)
    value = models.CharField(max_length=300, blank=True)

    def __str__(self):
        return self.key
