from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Staff user with a role. Each role lands on its own panel (REQ-SEC-1)."""

    class Role(models.TextChoices):
        ADMIN = "admin", "Admin"
        MANAGER = "manager", "Manager"
        EDITOR = "editor", "Editor"
        DISPATCH = "dispatch", "Dispatch"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.ADMIN)

    @property
    def home_url_name(self):
        return {
            self.Role.ADMIN: "panels:admin_dashboard",
            self.Role.MANAGER: "panels:manager_inventory",
            self.Role.EDITOR: "panels:editor_mockups",
            self.Role.DISPATCH: "panels:dispatch",
        }.get(self.role, "panels:admin_dashboard")


class Customer(models.Model):
    """A customer is identified by phone (the WhatsApp number). No password in v1."""

    name = models.CharField(max_length=120)
    phone = models.CharField(max_length=20, unique=True)
    whatsapp_verified = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.phone})"


class Attendance(models.Model):
    """Login/logout times per staff user (REQ-ATT-1)."""

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="attendance")
    login_ts = models.DateTimeField(auto_now_add=True)
    logout_ts = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-login_ts"]

    @property
    def status(self):
        return "Active" if self.logout_ts is None else "Done"
