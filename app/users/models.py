import uuid
from typing import Any

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    Group,
    Permission,
    PermissionsMixin,
)
from django.core.validators import EmailValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from organization.models import Organizations


# Custom user model for the application, including a custom user manager for handling user
# creation and superuser creation, with fields for email, full name, job title, operations location, role, and standard authentication fields.
class UserManager(BaseUserManager["User"]):
    def create_user(
        self, email: str, password: str | None = None, **extra_fields: Any
    ) -> "User":
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(
        self, email: str, password: str | None = None, **extra_fields: Any
    ) -> "User":
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(email, password, **extra_fields)



class Role(models.Model):
    """
    Stores the 8 fixed system roles scoped to an organization.
    Seeded automatically when an organization is created.
    Role names are fixed — they do not change per organization.
    """

    class RoleName(models.TextChoices):
        ORG_ADMIN = "org_admin", "Org Admin"
        MANAGEMENT = "management", "Management"
        LOGISTICS_OFFICER = "logistics_officer", "Logistics Officer"
        TRACKING_OFFICER = "tracking_officer", "Tracking Officer"
        WORKSHOP = "workshop", "Workshop"
        SALES = "sales", "Sales / Marketer"
        CUSTOMER = "customer", "Customer"
        DRIVER = "driver", "Driver"

    name = models.CharField(
        max_length=50,
        choices=RoleName.choices,
    )
    organization = models.ForeignKey(
        Organizations,
        on_delete=models.CASCADE,
        related_name="roles",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("name", "organization")
        ordering = ["name"]

    def __str__(self) -> str:
        return f"{self.get_name_display()} — {self.organization.name}"




class User(AbstractBaseUser, PermissionsMixin):
    """
    Account model with fields for email, full name, job title, operations location, role,
    and standard authentication fields,
    along with metadata and string representation.
    """
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    email = models.EmailField(
        _("email address"), unique=True, db_index=True, validators=[EmailValidator()]
    )
    organization = models.ForeignKey(Organizations, on_delete=models.CASCADE)
    role = models.ForeignKey(
        Role, on_delete=models.SET_NULL, null=True, blank=True, related_name="users"
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    groups = models.ManyToManyField(
        Group,
        related_name="custom_user_set",
        blank=True,
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name="custom_user_permissions_set",
        blank=True,
    )

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def __str__(self) -> str:
        return self.email


class UserProfile(models.Model):
    class Meta:
        abstract = True

    id = models.UUIDField(
        default=uuid.uuid4, primary_key=True, null=False, editable=False
    )
    user = models.OneToOneField(
        "User", on_delete=models.CASCADE, related_name="office_profile"
    )
    full_name = models.CharField(max_length=255, blank=True)
    job_title = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True, db_index=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.full_name


class OfficeProfile(UserProfile):
    # For office user profiles
    user = models.OneToOneField(
        "User", on_delete=models.CASCADE, related_name="office_profile"
    )
    display_photo = models.ImageField(upload_to="user_photos/", blank=True, null=True)


class DriverProfile(UserProfile):
    # For drivers profile
    user = models.OneToOneField(
        "User", on_delete=models.CASCADE, related_name="driver_profile"
    )
    license_number = models.CharField(max_length=255, blank=True, null=True)
    ops_location = models.CharField(
        max_length=255, blank=True, null=True, db_index=True
    )
