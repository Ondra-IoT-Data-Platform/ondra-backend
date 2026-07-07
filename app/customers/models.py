# customers/models.py

import uuid

from django.db import models
from django.utils import timezone

from organization.models import Organizations


class Customer(models.Model):
    """
    External customers who receive petroleum product deliveries.
    Created by Sales or Org Admin — not self-registered.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=20, blank=True, null=True, db_index=True)
    erp_code = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="ERP reference code for this customer — used for cross-system reconciliation",
    )
    address = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    organization = models.ForeignKey(
        Organizations,
        on_delete=models.CASCADE,
        related_name="customers",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("name", "organization")

    def __str__(self) -> str:
        return self.name


class CustomerContact(models.Model):
    """
    Named contacts at a customer site.
    Used for OTP delivery confirmation — the contact receives
    the OTP SMS when a driver signals arrival.
    A customer can have multiple contacts but only one primary.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="contacts",
    )
    full_name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20, db_index=True)
    email = models.EmailField(blank=True, null=True)
    job_title = models.CharField(max_length=255, blank=True, null=True)
    is_primary = models.BooleanField(
        default=False,
        help_text="Primary contact receives OTP for delivery confirmation",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_primary", "full_name"]

    def __str__(self) -> str:
        return f"{self.full_name} — {self.customer.name}"


class DeliveryAddress(models.Model):
    """
    Named delivery locations for a customer.
    A customer can have multiple delivery sites —
    e.g. Julius Berger may have sites in Abuja, Lagos, and Port Harcourt.
    The active address on a shipment determines which route and ETA are used.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="delivery_addresses",
    )
    label = models.CharField(
        max_length=255,
        help_text="Short name for this site e.g. Abuja Plant, Lagos Depot",
    )
    address = models.TextField()
    latitude = models.CharField(max_length=50, blank=True, null=True)
    longitude = models.CharField(max_length=50, blank=True, null=True)
    is_default = models.BooleanField(
        default=False,
        help_text="Default delivery address used when creating a shipment for this customer",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-is_default", "label"]

    def __str__(self) -> str:
        return f"{self.label} — {self.customer.name}"
