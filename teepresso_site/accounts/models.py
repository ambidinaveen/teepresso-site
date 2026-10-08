from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.crypto import get_random_string


class User(AbstractUser):
    """Single user model for staff and customers (PRINTPROX user roles).

    Roles drive RBAC: staff roles reach the dashboard; customers/corporate use
    the storefront + account area. Email is the primary login identifier.
    """

    class Role(models.TextChoices):
        SUPER_ADMIN = "super_admin", "Super Admin"
        ADMIN = "admin", "Admin"
        PRODUCT_MANAGER = "product_manager", "Product Manager"
        SUPPORT = "support", "Customer Support"
        CUSTOMER = "customer", "Customer"
        CORPORATE = "corporate", "Corporate Customer"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.CUSTOMER)
    phone = models.CharField(max_length=20, blank=True, db_index=True)
    company = models.CharField(max_length=160, blank=True)
    gst_number = models.CharField(max_length=20, blank=True)
    is_blocked = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    STAFF_ROLES = {Role.SUPER_ADMIN, Role.ADMIN, Role.PRODUCT_MANAGER, Role.SUPPORT}

    def __str__(self):
        return self.get_full_name() or self.username or self.email

    @property
    def is_staff_role(self):
        return self.role in self.STAFF_ROLES

    @property
    def display_name(self):
        return self.first_name or self.get_full_name() or self.email.split("@")[0]

    @property
    def default_address(self):
        return self.addresses.filter(is_default=True).first() or self.addresses.first()


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses")
    label = models.CharField(max_length=40, default="Home")
    full_name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20)
    line1 = models.CharField(max_length=200)
    line2 = models.CharField(max_length=200, blank=True)
    city = models.CharField(max_length=80)
    state = models.CharField(max_length=80)
    pincode = models.CharField(max_length=10)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_default", "id"]
        verbose_name_plural = "Addresses"

    def __str__(self):
        return f"{self.label}: {self.line1}, {self.city}"

    @property
    def one_line(self):
        bits = [self.line1, self.line2, self.city, self.state, self.pincode]
        return ", ".join(b for b in bits if b)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_default:
            self.user.addresses.exclude(pk=self.pk).update(is_default=False)


class WishlistItem(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wishlist_items")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "product")
        ordering = ["-created_at"]


class OTP(models.Model):
    """One-time code for registration / forgot-password (SMS/email safe-stub).

    In safe mode the code is shown on screen / printed to the console — no real
    SMS is sent until SMS_API is enabled with credentials.
    """

    class Purpose(models.TextChoices):
        REGISTER = "register", "Registration"
        RESET = "reset", "Password reset"

    identifier = models.CharField(max_length=120, db_index=True)  # email or phone
    code = models.CharField(max_length=6)
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    created_at = models.DateTimeField(auto_now_add=True)
    used = models.BooleanField(default=False)

    @classmethod
    def issue(cls, identifier, purpose):
        cls.objects.filter(identifier=identifier, purpose=purpose, used=False).update(used=True)
        return cls.objects.create(
            identifier=identifier, purpose=purpose, code=get_random_string(6, "0123456789")
        )

    def is_valid(self):
        age = timezone.now() - self.created_at
        return (not self.used) and age.total_seconds() < 600  # 10 min
