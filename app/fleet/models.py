# fleet/models.py

import uuid

from django.db import models
from django.utils import timezone

from organization.models import Organizations
from terminals.models import Terminals


class Product(models.Model):
    """Petroleum products carried by trucks."""

    class ProductType(models.TextChoices):
        # Motor Fuels
        PREMIUM_MOTOR_SPIRIT = (
            "premium_motor_spirit",
            "Premium Motor Spirit (PMS)"
        )
        AUTOMOTIVE_GAS_OIL = (
            "automotive_gas_oil",
            "Automotive Gas Oil (AGO)"
        )
        DUAL_PURPOSE_KEROSENE = (
            "dual_purpose_kerosene",
            "Dual Purpose Kerosene (DPK)"
        )
        HOUSEHOLD_KEROSENE = (
            "household_kerosene",
            "Household Kerosene (HHK)"
        )
        AVIATION_TURBINE_KEROSENE = (
            "aviation_turbine_kerosene",
            "Aviation Turbine Kerosene (ATK/Jet A-1)"
        )

        # Fuel Oils
        LOW_POUR_FUEL_OIL = (
            "low_pour_fuel_oil",
            "Low Pour Fuel Oil (LPFO)"
        )
        HEAVY_FUEL_OIL = (
            "heavy_fuel_oil",
            "Heavy Fuel Oil (HFO)"
        )

        # Gases
        LIQUEFIED_PETROLEUM_GAS = (
            "liquefied_petroleum_gas",
            "Liquefied Petroleum Gas (LPG)"
        )
        COMPRESSED_NATURAL_GAS = (
            "compressed_natural_gas",
            "Compressed Natural Gas (CNG)"
        )
        LIQUEFIED_NATURAL_GAS = (
            "liquefied_natural_gas",
            "Liquefied Natural Gas (LNG)"
        )
        NATURAL_GAS = (
            "natural_gas",
            "Natural Gas"
        )

        # Bitumen & Asphalt Products
        BITUMEN_60_70 = (
            "bitumen_60_70",
            "Bitumen 60/70"
        )
        BITUMEN_80_100 = (
            "bitumen_80_100",
            "Bitumen 80/100"
        )
        BITUMEN_40_50 = (
            "bitumen_40_50",
            "Bitumen 40/50"
        )
        POLYMER_MODIFIED_BITUMEN = (
            "polymer_modified_bitumen",
            "Polymer Modified Bitumen (PMB)"
        )
        CATIONIC_BITUMEN_EMULSION = (
            "cationic_bitumen_emulsion",
            "Cationic Bitumen Emulsion"
        )
        ANIONIC_BITUMEN_EMULSION = (
            "anionic_bitumen_emulsion",
            "Anionic Bitumen Emulsion"
        )
        CUTBACK_BITUMEN = (
            "cutback_bitumen",
            "Cutback Bitumen"
        )
        CRUMB_RUBBER_MODIFIED_BITUMEN = (
            "crumb_rubber_modified_bitumen",
            "Crumb Rubber Modified Bitumen (CRMB)"
        )

        # Lubricants
        ENGINE_OIL = (
            "engine_oil",
            "Engine Oil"
        )
        GEAR_OIL = (
            "gear_oil",
            "Gear Oil"
        )
        HYDRAULIC_OIL = (
            "hydraulic_oil",
            "Hydraulic Oil"
        )
        TRANSMISSION_FLUID = (
            "transmission_fluid",
            "Transmission Fluid"
        )
        GREASE = (
            "grease",
            "Grease"
        )

        # Industrial Products
        BASE_OIL = (
            "base_oil",
            "Base Oil"
        )
        PARAFFIN_WAX = (
            "paraffin_wax",
            "Paraffin Wax"
        )
        SOLVENT = (
            "solvent",
            "Industrial Solvent"
        )

        # Marine
        MARINE_GAS_OIL = (
            "marine_gas_oil",
            "Marine Gas Oil (MGO)"
        )
        MARINE_DIESEL_OIL = (
            "marine_diesel_oil",
            "Marine Diesel Oil (MDO)"
        )


    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=100,
        choices=ProductType.choices,
        unique=True,
    )
    description = models.TextField(blank=True, null=True)
    unit = models.CharField(
        max_length=20,
        default="litres",
        help_text="Unit of measurement e.g. litres, tonnes, kg",
    )
    organization = models.ForeignKey(
        Organizations,
        on_delete=models.CASCADE,
        related_name="products",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        unique_together = ("name", "organization")

    def __str__(self) -> str:
        return self.get_name_display()


class Route(models.Model):
    """
    Standardized routes between terminals and customer destinations.
    Reused across shipments to enable distance and TAT comparisons.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    route_name = models.CharField(max_length=255)
    origin_terminal = models.ForeignKey(
        Terminals,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="outbound_routes",
    )
    destination = models.CharField(
        max_length=255,
        help_text="Customer delivery location name or address",
    )
    standard_distance_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    expected_tat_hours = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Expected turnaround time in hours",
    )
    organization = models.ForeignKey(
        Organizations,
        on_delete=models.CASCADE,
        related_name="routes",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["route_name"]
        unique_together = ("route_name", "organization")

    def __str__(self) -> str:
        return self.route_name


class Truck(models.Model):
    """
    Registered trucks in the fleet.
    Tracks operational status, RFID tag, home terminal, and default product.
    """

    class StatusChoices(models.TextChoices):
        OUTBOUND = "outbound", "Outbound"
        INBOUND = "inbound", "Inbound"
        ARRIVED = "arrived", "Arrived"
        AT_CUSTOMER = "at_customer", "At Customer"
        FAULTY = "faulty", "Faulty"
        AT_TERMINAL = "at_terminal", "At Terminal"
        PARKED = "parked", "Parked"
        UNDER_MAINTENANCE = "under_maintenance", "Under Maintenance"
        DECOMMISSIONED = "decommissioned", "Decommissioned"

    class TruckType(models.TextChoices):
        TANKER = "tanker", "Tanker"
        FLATBED = "flatbed", "Flatbed"
        REFRIGERATED = "refrigerated", "Refrigerated"
        TOW_TRUCK = "tow_truck", "Tow Truck"
        CRANE_TRUCK = "crane_truck", "Crane Truck"
        CARRIER_TRUCK = "carrier_truck", "Carrier Truck"
        DUMP_TRUCK = "dump_truck", "Dump Truck"
        MIXER_TRUCK = "mixer_truck", "Mixer Truck"
        SEMI_TRUCK = "semi_truck", "Semi Truck"
        SPRAYER = "sprayer", "Sprayer"
        CONTAINER_TRUCK = "container", "Container Truck"
        BULK = "bulk", "Bulk Carrier"
        OTHER = "other", "Other"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    plate_number = models.CharField(max_length=50, unique=True, db_index=True)
    truck_type = models.CharField(
        max_length=50,
        choices=TruckType.choices,
        default=TruckType.TANKER,
    )
    capacity = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Capacity in litres",
    )
    current_status = models.CharField(
        max_length=30,
        choices=StatusChoices.choices,
        default=StatusChoices.PARKED,
        db_index=True,
    )
    default_product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trucks",
        help_text="Default product this truck carries — overridable per shipment",
    )
    home_terminal = models.ForeignKey(
        Terminals,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="trucks",
        help_text="Primary terminal this truck is based at",
    )
    rfid_tag_id = models.CharField(
        max_length=100,
        unique=True,
        null=True,
        blank=True,
        db_index=True,
        help_text="RFID tag EPC number attached to this truck",
    )
    is_active = models.BooleanField(default=True)
    organization = models.ForeignKey(
        Organizations,
        on_delete=models.CASCADE,
        related_name="trucks",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["plate_number"]

    def __str__(self) -> str:
        return self.plate_number


class TruckLocation(models.Model):
    """
    Latest GPS location for a truck synced from the third-party provider.
    One row per truck — updated in place on every sync, not appended.
    Stores enough data to power the live fleet map on the dashboard.
    """

    truck = models.OneToOneField(
        Truck,
        on_delete=models.CASCADE,
        related_name="location",
        primary_key=True,
    )
    latitude = models.CharField(max_length=50)
    longitude = models.CharField(max_length=50)
    speed_kmh = models.FloatField(null=True, blank=True)
    bearing = models.FloatField(
        null=True,
        blank=True,
        help_text="Direction of travel in degrees 0-360",
    )
    provider = models.CharField(
        max_length=100,
        default="gambus",
        help_text="GPS provider that supplied this data point",
    )
    last_synced = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Truck Location"
        verbose_name_plural = "Truck Locations"

    def __str__(self) -> str:
        return f"{self.truck.plate_number} — {self.latitude}, {self.longitude}"


class TruckStatusLog(models.Model):
    """
    Audit trail of every truck status change.
    Records what changed, when, how it was triggered, and who triggered it.
    Powers the truck history view and driver performance analysis.
    """

    class TriggerSource(models.TextChoices):
        RFID = "rfid", "RFID Gate Event"
        MANUAL = "manual", "Manual Override"
        GPS = "gps", "GPS Sync"
        SYSTEM = "system", "System"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    truck = models.ForeignKey(
        Truck,
        on_delete=models.CASCADE,
        related_name="status_logs",
    )
    previous_status = models.CharField(
        max_length=30,
        choices=Truck.StatusChoices.choices,
        null=True,
        blank=True,
    )
    new_status = models.CharField(
        max_length=30,
        choices=Truck.StatusChoices.choices,
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
        related_name="truck_status_changes",
        help_text="The user who triggered this change — null if triggered by RFID or GPS",
    )
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return (
            f"{self.truck.plate_number} "
            f"{self.previous_status} → {self.new_status} "
            f"({self.trigger_source})"
        )
