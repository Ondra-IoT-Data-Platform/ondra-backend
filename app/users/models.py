import uuid
from typing import Any

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.core.validators import EmailValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from app.organization.models import Organizations


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

        return self.create_user(email, password, **extra_fields)


class UserRole(models.Model):
    title = models.CharField(max_length=20, unique=True)


# Account model with fields for email, full name, job title, operations location, role, and standard authentication fields,
# along with metadata and string representation.
class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True, editable=False)
    email = models.EmailField(
        _("email address"), unique=True, db_index=True, validators=[EmailValidator()]
    )
    organization = models.ForeignKey(Organizations, on_delete=models.CASCADE)
    role = models.OneToOneField(UserRole, on_delete=models.SET_NULL)
    password = models.CharField(max_length=50, null=False, default="")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")

    def __str__(self) -> str:
        return self.email


class UserProfile(models.Model):
    id = models.UUIDField(
        default=uuid.uuid4, primary_key=True, null=False, editable=False
    )
    user = models.OneToOneField("User", on_delete=models.CASCADE)
    full_name = models.CharField(max_length=255, blank=True)
    job_title = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True, db_index=True)

    def __str__(self) -> str:
        return self.full_name


class OfficeProfile(UserProfile):
    display_photo = models.ImageField(
        upload_to="/app/mediafiles/user_photos/", blank=True, null=True
    )


class DriverProfile(UserProfile):
    license_number = models.CharField(max_length=255, blank=True, null=True)
    ops_location = models.CharField(
        max_length=255, blank=True, null=True, db_index=True
    )
    # terminal =
