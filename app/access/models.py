import uuid
from django.conf import settings
from django.db import models
from django.utils import timezone
from organization.models import Organizations
# from users.models import User

#TODO: RUN MIGRATION ON THIS FILE
class TokenTypeChoices(models.TextChoices):
    USER_ONBOARDING = "user_onboarding", "User Onboarding"
    EMAIL_VERIFICATION = "email_verification", "Email Verification"
    INVITATION = "invitation", "Invitation"
    PASSWORD_RESET = "password_reset", "Password Reset"
    TWO_FACTOR_AUTH = "two_factor_auth", "Two Factor Authentication"
    REFRESH_TOKEN = "refresh_token", "Refresh Token"
    DELIVERY_CONFIRMATION = "delivery_confirmation", "Delivery Confirmation"


class OrganizationTokens(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    token = models.CharField(max_length=255, unique=True, db_index=True, default="")
    token_hash = models.CharField(max_length=64, unique=True, db_index=True, default="")
    token_type = models.CharField(max_length=255, choices=TokenTypeChoices.choices)
    email = models.EmailField(max_length=255, null=True, blank=True) # for pre-onboarding invitations
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_tokens",
        null=True, blank=True
    )
    organization = models.ForeignKey(Organizations, on_delete=models.CASCADE, related_name="organization_tokens", null=True)
    is_used = models.BooleanField(default=False)
    is_revoked = models.BooleanField(default=False)
    metadata = models.JSONField(null=True, blank=True, default=dict)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        indexes = [
            models.Index(fields=["token_hash"]),
            models.Index(fields=["user"]),
            models.Index(fields=["token_type"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["token_hash", "token_type", "user"]),
        ]

    def __str__(self) -> str:
        if self.user:
            return f"{self.token_type} token for user {self.user.id}"
        elif self.email:
            return f"{self.token_type} token for {self.email}"
        else:
            return f"{self.token_type} token (ID: {self.id})"

    @property
    def is_expired(self):
        return timezone.now() > self.expires_at

    @property
    def is_valid(self):
        return not self.is_used and not self.is_expired



class UserSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sessions")
    refresh_token = models.TextField(unique=True)
    device_info = models.CharField(max_length=255, null=True, blank=True)
    ip_address = models.CharField(max_length=50, null=True, blank=True)
    last_active_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True, default=None)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Session for {self.user.email} (Last Active: {self.last_active_at})"

    @property
    def is_valid(self):
        return self.revoked_at is None and timezone.now() < self.expires_at

    def revoke(self):
        self.revoked_at = timezone.now()
        self.save(update_fields=["revoked_at"])
