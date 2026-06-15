from uuid import uuid4

from django.db import models


class Organizations(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    industry = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


# -------- FUTURE INTEGRATION TO PUT IN --------------
class OrganizationSettings(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    organization = models.OneToOneField(
        Organizations, on_delete=models.CASCADE, related_name="settings"
    )
    timezone = models.CharField(max_length=255, blank=True, null=True)
    language = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Settings for {self.organization.name}"
