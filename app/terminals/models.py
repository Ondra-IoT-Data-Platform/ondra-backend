from django.db import models
from django.utils import timezone

from app.organization.models import Organizations


class Terminals(models.Model):
    class StatusChoices(models.TextChoices):
        ACTIVE = "active", "Active"
        CLOSED = "closed", "Closed"
        DECOMMISSIONED = "decommissioned", "Decommissioned"

    name = models.CharField(max_length=255, null=False, blank=False)
    location = models.CharField(max_length=255)
    longitude = models.CharField(max_length=50, db_index=True)
    latitude = models.CharField(max_length=50, db_index=True)
    organization = models.ForeignKey(
        Organizations,
        on_delete=models.CASCADE,
        related_name="terminals",
    )
    status = models.CharField(
        max_length=20,
        choices=StatusChoices.choices,
        default=StatusChoices.ACTIVE,
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return self.name


class Gates(models.Model):
    class GateTypeChoices(models.TextChoices):
        ENTRY = "entry", "Entry"
        EXIT = "exit", "Exit"
        BAY = "bay", "Bay"
        WORKSHOP = "workshop", "WORKSHOP"

    terminal = models.ForeignKey(
        Terminals,
        on_delete=models.CASCADE,
        related_name="gates",
    )
    name = models.CharField(max_length=50)
    gate_type = models.CharField(
        max_length=50,
        choices=GateTypeChoices.choices,
        default=GateTypeChoices.ENTRY,
    )

    def __str__(self) -> str:
        return f"{self.name} ({self.terminal.name})"
