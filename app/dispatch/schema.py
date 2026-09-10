from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from ninja import ModelSchema, Schema

from dispatch.models import (
    Dispatch,
    DeliveryConfirmation,
    DispatchStatusLog,
    TripMetadata,
)


# ── Dispatch ───────────────────────────────────────────────

class DispatchCreateSchema(Schema):
    """Creates a new dispatch / TMR."""
    waybill_number: str
    sales_order_no: Optional[str] = None
    truck_id: UUID
    driver_id: UUID
    customer_id: UUID
    delivery_address_id: Optional[UUID] = None
    origin_terminal_id: Optional[int] = None
    route_id: Optional[UUID] = None
    product_id: UUID
    quantity: Decimal
    expected_departure: Optional[datetime] = None
    notes: Optional[str] = None


class DispatchUpdateSchema(Schema):
    """Partially updates a dispatch — only permitted before dispatched status."""
    sales_order_no: Optional[str] = None
    truck_id: Optional[UUID] = None
    driver_id: Optional[UUID] = None
    delivery_address_id: Optional[UUID] = None
    route_id: Optional[UUID] = None
    product_id: Optional[UUID] = None
    quantity: Optional[Decimal] = None
    expected_departure: Optional[datetime] = None
    notes: Optional[str] = None


class DispatchStatusUpdateSchema(Schema):
    """Manual dispatch status override."""
    status: str
    note: Optional[str] = None


class DispatchOutSchema(ModelSchema):
    """Full dispatch output."""
    class Meta:
        model = Dispatch
        fields = [
            "id",
            "waybill_number",
            "sales_order_no",
            "truck",
            "driver",
            "customer",
            "delivery_address",
            "origin_terminal",
            "route",
            "product",
            "quantity",
            "status",
            "expected_departure",
            "actual_departure",
            "actual_arrival",
            "eta",
            "arrival_token_attempts",
            "notes",
            "organization",
            "created_by",
            "created_at",
            "updated_at",
        ]


class DispatchListOutSchema(ModelSchema):
    """Lightweight dispatch output for list views."""
    class Meta:
        model = Dispatch
        fields = [
            "id",
            "waybill_number",
            "truck",
            "driver",
            "customer",
            "product",
            "quantity",
            "status",
            "expected_departure",
            "actual_departure",
            "actual_arrival",
            "eta",
            "created_at",
        ]


class DispatchStatusLogOutSchema(ModelSchema):
    """Single dispatch status log entry."""
    class Meta:
        model = DispatchStatusLog
        fields = [
            "id",
            "dispatch",
            "previous_status",
            "new_status",
            "trigger_source",
            "triggered_by",
            "note",
            "created_at",
        ]


# ── Trip Metadata ──────────────────────────────────────────

class TripMetadataCreateSchema(ModelSchema):
    """Creates trip metadata for a dispatch."""
    class Meta:
        model = TripMetadata
        fields = [
            "scale_in_time",
            "scale_out_time",
            "tare_weight",
            "gross_weight",
            "net_weight",
            "rob",
            "seal_numbers",
            "loading_temp",
            "fuel_intank",
            "odometer_departure",
            "odometer_arrival",
            "remarks",
        ]
        fields_optional = "__all__"


class TripMetadataUpdateSchema(ModelSchema):
    """Partially updates trip metadata."""
    class Meta:
        model = TripMetadata
        fields = [
            "scale_in_time",
            "scale_out_time",
            "tare_weight",
            "gross_weight",
            "net_weight",
            "rob",
            "seal_numbers",
            "loading_temp",
            "fuel_intank",
            "odometer_departure",
            "odometer_arrival",
            "remarks",
        ]
        fields_optional = "__all__"


class TripMetadataOutSchema(ModelSchema):
    """Trip metadata output."""
    actual_distance_km: Optional[int] = None

    class Meta:
        model = TripMetadata
        fields = [
            "dispatch",
            "scale_in_time",
            "scale_out_time",
            "tare_weight",
            "gross_weight",
            "net_weight",
            "rob",
            "seal_numbers",
            "loading_temp",
            "fuel_intank",
            "odometer_departure",
            "odometer_arrival",
            "remarks",
            "created_at",
            "updated_at",
        ]

    @staticmethod
    def resolve_actual_distance_km(obj: TripMetadata) -> Optional[int]:
        return obj.actual_distance_km


# ── Delivery Confirmation ──────────────────────────────────

class DeliveryConfirmationCreateSchema(Schema):
    """
    Submitted by customer when confirming delivery via OTP.
    OTP validation happens in the service before this is processed.
    """
    otp: str
    confirmed_by_name: str
    confirmed_by_phone: str
    waybridge_weight: Decimal


class DeliveryConfirmationOutSchema(ModelSchema):
    """Delivery confirmation output."""
    class Meta:
        model = DeliveryConfirmation
        fields = [
            "id",
            "dispatch",
            "confirmed_by_name",
            "confirmed_by_phone",
            "waybridge_weight",
            "variance",
            "variance_percentage",
            "is_flagged",
            "confirmed_at",
        ]


# ── Driver arrival ─────────────────────────────────────────

class DriverArrivalSchema(Schema):
    """
    Posted by driver when they arrive at customer site.
    Triggers OTP generation and SMS to customer.
    """
    dispatch_id: UUID


# ── OTP resend ─────────────────────────────────────────────

class ResendOTPSchema(Schema):
    """Resends OTP to customer — driver or tracking officer only."""
    dispatch_id: UUID
