from uuid import uuid4


from django.db import models
from django.utils import timezone
from django.conf import settings


class Organizations(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True)
    industry = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    # created_at = models.DateTimeField(auto_now_add=True)
    # updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


# -------- FUTURE INTEGRATION TO PUT IN --------------
class OrganizationSettings(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    organization = models.OneToOneField(
        Organizations, on_delete=models.CASCADE, related_name="settings"
    )
    time_zone = models.CharField(max_length=255, blank=True, null=True)
    language = models.CharField(max_length=255, blank=True, null=True)
    # created_at = models.DateTimeField(auto_now_add=True)
    # updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"Settings for {self.organization.name}"


class OrganizationMember(models.Model):
    class RoleChoices(models.TextChoices):
            ORG_ADMIN = "org_admin", "Org Admin"
            MANAGEMENT = "management", "Management"
            LOGISTICS_OFFICER = "logistics_officer", "Logistics Officer"
            TRACKING_OFFICER = "tracking_officer", "Tracking Officer"
            WORKSHOP = "workshop", "Workshop"
            SALES = "sales", "Sales / Marketer"
            CUSTOMER = "customer", "Customer"
            DRIVER = "driver", "Driver"

    id = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    organization = models.ForeignKey(Organizations, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='organization_memberships')
    role = models.CharField(max_length=20, choices=RoleChoices, default=RoleChoices.LOGISTICS_OFFICER)
    joined_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        db_table = 'organization_members'
        unique_together = [['organization', 'user']]
        indexes = [
            models.Index(fields=['organization', 'user']),
            models.Index(fields=['role']),
        ]
