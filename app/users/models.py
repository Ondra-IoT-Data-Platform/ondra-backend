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
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)

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
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    last_login = None
    last_login_at = models.DateTimeField(null=True, blank=True, default=None)
    deleted_at = models.DateTimeField(null=True, blank=True, default=None)

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
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["is_active"]),
        ]

    def __str__(self) -> str:
        return self.email

    def update_last_login(self):
        """Call this on successful login instead of Django's built-in."""
        self.last_login_at = timezone.now()
        self.save(update_fields=["last_login_at", "updated_at"])

    def soft_delete(self):
        """Soft delete — marks deleted_at and deactivates the user."""
        self.deleted_at = timezone.now()
        self.is_active = False
        self.save(update_fields=["deleted_at", "is_active", "updated_at"])


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
