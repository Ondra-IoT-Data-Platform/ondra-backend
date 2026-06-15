from django.conf import settings
from django.db import models


class TokenTypeChoices(models.TextChoices):
    EMAIL_VERIFICATION = "email_verification", "Email Verification"
    PASSWORD_RESET = "password_reset", "Password Reset"
    TWO_FACTOR_AUTH = "two_factor_auth", "Two Factor Authentication"


class VerificationTokens(models.Model):
    token_hash = models.CharField(max_length=64, unique=True, db_index=True, default="")
    token_type = models.CharField(max_length=255, choices=TokenTypeChoices.choices)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tokens"
    )
    is_used = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["token_hash"]),
            models.Index(fields=["user"]),
            models.Index(fields=["token_type"]),
            models.Index(fields=["expires_at"]),
            models.Index(fields=["token_hash", "token_type", "user"]),
        ]

    def __str__(self) -> str:
        return f"{self.token_type} token for user {self.user.id}"
