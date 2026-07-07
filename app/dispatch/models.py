# dispatch/models.py

import uuid

from django.db import models
from django.utils import timezone

from customers.models import Customer, DeliveryAddress
from fleet.models import Product, Route, Truck
from organization.models import Organizations
from terminals.models import Terminals


class Dispatch(models.Model):
    """
    A Transport Movement Record (TMR) — the primary dispatch document.
    Created by Logistics Officer or Terminal Head when a truck is assigned
    to deliver a product to a customer.
    One dispatch = one truck trip = one waybill.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        LOADING = "loading", "Loading"
        DISPATCHED = "dispatched", "Dispatched"
        IN_TRANSIT = "in_transit", "In Transit"
        ARRIVED = "arrived", "Arrived at Customer"
        DELIVERED = "delivered", "Delivered"
        CANCELLED = "cancelled", "Cancelled"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    waybill_number = models.CharField(
        max_length=100,
        unique=True,
        db_index=True,
    )
    sales_order_no = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        help_text="ERP sales order reference number",
    )
    truck = models.ForeignKey(
        Truck,
        on_delete=models.RESTRICT,
        related_name="dispatches",
    )
    driver = models.ForeignKey(
        "users.User",
        on_delete=models.RESTRICT,
        related_name="dispatches",
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.RESTRICT,
        related_name="dispatches",
    )
    delivery_address = models.ForeignKey(
        DeliveryAddress,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dispatches",
    )
    origin_terminal = models.ForeignKey(
        Terminals,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dispatches",
    )
    route = models.ForeignKey(
        Route,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dispatches",
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.RESTRICT,
        related_name="dispatches",
    )
    quantity = models.DecimalField(
        max_digits=12,
        decimal_places=3,
        help_text="Quantity dispatched in the product's unit of measurement",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
        db_index=True,
    )
    expected_departure = models.DateTimeField(
        null=True,
        blank=True,
    )
    actual_departure = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Set automatically when RFID gate exit event is processed",
    )
    eta = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Estimated time of arrival — computed by ETA prediction module",
    )
    arrival_token = models.CharField(
        max_length=6,
        null=True,
        blank=True,
        help_text="6-digit OTP sent to customer on driver arrival — null until status is ARRIVED",
    )
    arrival_token_expires_at = models.DateTimeField(
        null=True,
        blank=True,
    )
    arrival_token_attempts = models.PositiveSmallIntegerField(default=0)
    notes = models.TextField(blank=True, null=True)
    organization = models.ForeignKey(
        Organizations,
        on_delete=models.CASCADE,
        related_name="dispatches",
    )
    created_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_dispatches",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.waybill_number} — {self.truck.plate_number}"

    @property
    def is_active(self) -> bool:
        """True if truck cannot be assigned to another dispatch."""
        return self.status in [
            self.Status.LOADING,
            self.Status.DISPATCHED,
            self.Status.IN_TRANSIT,
            self.Status.ARRIVED,
        ]

    @property
    def otp_is_valid(self) -> bool:
        """True if arrival token exists, not expired, and attempts not exceeded."""
        if not self.arrival_token:
            return False
        if self.arrival_token_attempts >= 3:
            return False
        if self.arrival_token_expires_at and timezone.now() > self.arrival_token_expires_at:
            return False
        return True


class TripMetadata(models.Model):
    """
    Weighbridge and loading data recorded at the terminal.
    Mandatory for every dispatch — the 1:1 record containing
    high-volume operational data from the loading process.
    """

    dispatch = models.OneToOneField(
        Dispatch,
        on_delete=models.CASCADE,
        related_name="trip_metadata",
        primary_key=True,
    )
    scale_in_time = models.DateTimeField(null=True, blank=True)
    scale_out_time = models.DateTimeField(null=True, blank=True)
    tare_weight = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Empty truck weight in tonnes",
    )
    gross_weight = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Loaded truck weight in tonnes",
    )
    net_weight = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Product weight — gross minus tare",
    )
    rob = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Remaining on board — product left in truck from previous trip",
    )
    seal_numbers = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Comma-separated seal numbers applied at loading",
    )
    loading_temp = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Product temperature at loading in degrees Celsius",
    )
    fuel_intank = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Fuel level at departure in litres",
    )
    odometer_departure = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Odometer reading at departure in km",
    )
    odometer_arrival = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Odometer reading at arrival in km — used for mileage fraud detection",
    )
    remarks = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Trip Metadata"
        verbose_name_plural = "Trip Metadata"

    def __str__(self) -> str:
        return f"Metadata — {self.dispatch.waybill_number}"

    @property
    def actual_distance_km(self) -> int | None:
        """Actual distance travelled — odometer arrival minus departure."""
        if self.odometer_departure and self.odometer_arrival:
            return self.odometer_arrival - self.odometer_departure
        return None


class DeliveryConfirmation(models.Model):
    """
    Records the customer's delivery confirmation event.
    Captures waybridge weight at customer site and computes
    variance against dispatched quantity for loss detection.
    Created when customer submits valid OTP.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dispatch = models.OneToOneField(
        Dispatch,
        on_delete=models.CASCADE,
        related_name="delivery_confirmation",
    )
    confirmed_by_name = models.CharField(
        max_length=255,
        help_text="Name of customer contact who confirmed delivery",
    )
    confirmed_by_phone = models.CharField(max_length=20)
    waybridge_weight = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        help_text="Quantity recorded at customer waybridge in product unit",
        blank=True,
        null=True
    )
    variance = models.DecimalField(
        max_digits=10,
        decimal_places=3,
        null=True,
        blank=True,
        help_text="Dispatched quantity minus waybridge weight — computed on save",
    )
    variance_percentage = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        null=True,
        blank=True,
    )
    is_flagged = models.BooleanField(
        default=False,
        help_text="True if variance exceeds the configured threshold",
    )
    confirmed_at = models.DateTimeField(default=timezone.now)

    class Meta:
        verbose_name = "Delivery Confirmation"

    def __str__(self) -> str:
        return f"Confirmed — {self.dispatch.waybill_number}"

    def save(self, *args, **kwargs) -> None:
        """Auto-compute variance and flag on save."""
        dispatched = self.dispatch.quantity
        received = self.waybridge_weight

        self.variance = dispatched - received

        if dispatched > 0:
            self.variance_percentage = (self.variance / dispatched) * 100

        # Flag if variance exceeds 2 percent
        threshold = 2.0
        if self.variance_percentage and abs(self.variance_percentage) > threshold:
            self.is_flagged = True

        super().save(*args, **kwargs)


class DispatchStatusLog(models.Model):
    """
    Audit trail of every dispatch status change.
    Powers the shipment timeline visible to customers and tracking officers.
    """

    class TriggerSource(models.TextChoices):
        RFID = "rfid", "RFID Gate Event"
        MANUAL = "manual", "Manual Override"
        DRIVER = "driver", "Driver Action"
        CUSTOMER = "customer", "Customer Confirmation"
        SYSTEM = "system", "System"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    dispatch = models.ForeignKey(
        Dispatch,
        on_delete=models.CASCADE,
        related_name="status_logs",
    )
    previous_status = models.CharField(
        max_length=20,
        choices=Dispatch.Status.choices,
        null=True,
        blank=True,
    )
    new_status = models.CharField(
        max_length=20,
        choices=Dispatch.Status.choices,
    )
    trigger_source = models.CharField(
        max_length=20,
        choices=TriggerSource.choices,
        default=TriggerSource.SYSTEM,
    )
    triggered_by = models.ForeignKey(
        "users.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="dispatch_status_changes",
    )
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return (
            f"{self.dispatch.waybill_number} "
            f"{self.previous_status} → {self.new_status}"
        )
