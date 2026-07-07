from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from ninja import ModelSchema, Schema

from fleet.models import Product, Route, Truck, TruckLocation, TruckStatusLog


# ── Product ────────────────────────────────────────────────

class ProductOutSchema(ModelSchema):
    """Product output."""
    class Meta:
        model = Product
        fields = [
            "id", "name", "description",
            "unit", "organization", "created_at",
        ]


class ProductCreateSchema(ModelSchema):
    """Creates a product."""
    class Meta:
        model = Product
        fields = ["name", "description", "unit"]
        fields_optional = ["description", "unit"]


class ProductUpdateSchema(ModelSchema):
    """Partially updates a product."""
    class Meta:
        model = Product
        fields = ["description", "unit"]
        fields_optional = "__all__"


# ── Route ──────────────────────────────────────────────────

class RouteOutSchema(ModelSchema):
    """Route output."""
    class Meta:
        model = Route
        fields = [
            "id", "route_name", "origin_terminal",
            "destination", "standard_distance_km",
            "expected_tat_hours", "organization", "created_at",
        ]


class RouteCreateSchema(ModelSchema):
    """Creates a route."""
    class Meta:
        model = Route
        fields = [
            "route_name", "origin_terminal", "destination",
            "standard_distance_km", "expected_tat_hours",
        ]
        fields_optional = [
            "origin_terminal", "standard_distance_km", "expected_tat_hours",
        ]


class RouteUpdateSchema(ModelSchema):
    """Partially updates a route."""
    class Meta:
        model = Route
        fields = [
            "route_name", "destination",
            "standard_distance_km", "expected_tat_hours",
        ]
        fields_optional = "__all__"


# ── Truck ──────────────────────────────────────────────────

class TruckLocationOutSchema(ModelSchema):
    """Truck location output."""
    class Meta:
        model = TruckLocation
        fields = [
            "latitude", "longitude", "speed_kmh",
            "bearing", "provider", "last_synced",
        ]


class TruckOutSchema(ModelSchema):
    """Truck output including latest location if available."""
    location: Optional[TruckLocationOutSchema] = None

    class Meta:
        model = Truck
        fields = [
            "id", "plate_number", "truck_type", "capacity",
            "current_status", "default_product", "home_terminal",
            "rfid_tag_id", "is_active", "organization",
            "created_at", "updated_at",
        ]

    @staticmethod
    def resolve_location(obj) -> Optional[TruckLocationOutSchema]:
        try:
            return TruckLocationOutSchema.from_orm(obj.location)
        except TruckLocation.DoesNotExist:
            return None


class TruckCreateSchema(ModelSchema):
    """Registers a new truck."""
    class Meta:
        model = Truck
        fields = [
            "plate_number", "truck_type", "capacity",
            "default_product", "home_terminal", "rfid_tag_id",
        ]
        fields_optional = [
            "truck_type", "capacity", "default_product",
            "home_terminal", "rfid_tag_id",
        ]


class TruckUpdateSchema(ModelSchema):
    """Partially updates a truck."""
    class Meta:
        model = Truck
        fields = [
            "plate_number", "truck_type", "capacity",
            "default_product", "home_terminal",
            "rfid_tag_id", "is_active",
        ]
        fields_optional = "__all__"


class TruckStatusUpdateSchema(Schema):
    """Manual truck status override."""
    status: str
    note: Optional[str] = None


class TruckStatusLogOutSchema(ModelSchema):
    """Single status log entry output."""
    class Meta:
        model = TruckStatusLog
        fields = [
            "id", "truck", "previous_status", "new_status",
            "trigger_source", "triggered_by", "note", "created_at",
        ]
