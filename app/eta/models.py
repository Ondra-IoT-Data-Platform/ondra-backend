import uuid
from django.db import models
from django.utils import timezone
from organization.models import Organizations


class ETATripRecord(models.Model):
    """
    Training record created automatically on every confirmed delivery.
    Each row is one completed trip used to train the XGBoost ETA model.
    No manual data entry required — populated from dispatch and confirmation data.
    """
    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    dispatch = models.OneToOneField(
        "dispatch.Dispatch",
        on_delete=models.CASCADE,
        related_name="eta_record",
    )
    organization = models.ForeignKey(
        Organizations,
        on_delete=models.CASCADE,
        related_name="eta_records",
    )
    distance_km = models.FloatField(null=True, blank=True)
    base_eta_minutes = models.FloatField(
        null=True, blank=True,
        help_text="Stage 1 routing API estimate in minutes",
    )
    hour_of_day = models.PositiveSmallIntegerField(null=True, blank=True)
    day_of_week = models.PositiveSmallIntegerField(null=True, blank=True)
    driver_id = models.UUIDField(null=True, blank=True, db_index=True)
    origin_terminal_id = models.IntegerField(null=True, blank=True)
    product_name = models.CharField(max_length=100, blank=True, null=True)
    quantity = models.FloatField(null=True, blank=True)
    actual_duration_minutes = models.FloatField(
        help_text="Actual trip duration — the target variable for model training",
    )
    departed_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["organization", "created_at"]),
            models.Index(fields=["driver_id"]),
            models.Index(fields=["origin_terminal_id"]),
        ]

    def __str__(self) -> str:
        return (
            f"ETA Record — {self.dispatch_id} "
            f"— {self.actual_duration_minutes} min"
        )


class ETAModelVersion(models.Model):
    """
    Versioned history of trained XGBoost models per organization.
    One active version at a time — previous versions retired on new training run.
    """
    class Status(models.TextChoices):
        TRAINING = "training", "Training"
        ACTIVE = "active", "Active"
        RETIRED = "retired", "Retired"
        FAILED = "failed", "Failed"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    organization = models.ForeignKey(
        Organizations,
        on_delete=models.CASCADE,
        related_name="eta_model_versions",
    )
    version = models.PositiveIntegerField()
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.TRAINING,
        db_index=True,
    )
    records_used = models.PositiveIntegerField()
    mae_minutes = models.FloatField(null=True, blank=True)
    rmse_minutes = models.FloatField(null=True, blank=True)
    mape_percentage = models.FloatField(null=True, blank=True)
    model_file_path = models.CharField(
        max_length=500, blank=True, null=True,
    )
    trained_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-version"]
        unique_together = ("organization", "version")

    def __str__(self) -> str:
        return (
            f"ETA Model v{self.version} "
            f"— {self.organization.name} — {self.status}"
        )
