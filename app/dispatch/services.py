import asyncio
import logging
import secrets
import nest_asyncio
from datetime import timedelta
from uuid import UUID

from django.utils import timezone

from config.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from dispatch.models import (
    DeliveryConfirmation,
    Dispatch,
    DispatchStatusLog,
    TripMetadata,
)
from dispatch.schema import (
    DeliveryConfirmationCreateSchema,
    DeliveryConfirmationOutSchema,
    DispatchCreateSchema,
    DispatchListOutSchema,
    DispatchOutSchema,
    DispatchStatusLogOutSchema,
    DispatchStatusUpdateSchema,
    DispatchUpdateSchema,
    TripMetadataCreateSchema,
    TripMetadataOutSchema,
    TripMetadataUpdateSchema,
)
from fleet.models import Truck
from users.models import User

nest_asyncio.apply()

logger = logging.getLogger(__name__)

# ── Helpers ────────────────────────────────────────────────

def _generate_otp() -> str:
    """Generates a cryptographically secure 6-digit OTP."""
    return str(secrets.randbelow(900000) + 100000)


def _write_dispatch_status_log(
    dispatch: Dispatch,
    previous_status: str,
    new_status: str,
    trigger_source: str,
    triggered_by: User | None = None,
    note: str | None = None,
) -> None:
    DispatchStatusLog.objects.create(
        dispatch=dispatch,
        previous_status=previous_status,
        new_status=new_status,
        trigger_source=trigger_source,
        triggered_by=triggered_by,
        note=note,
    )


def _dispatch_qs():
    return Dispatch.objects.select_related(
        "truck",
        "driver",
        "customer",
        "delivery_address",
        "origin_terminal",
        "route",
        "product",
        "organization",
        "created_by",
    )


# ── Dispatch services ──────────────────────────────────────

def create_dispatch_service(
    data: DispatchCreateSchema,
    organization_id: UUID,
    created_by_id: str,
) -> DispatchOutSchema:
    """
    Creates a new dispatch record.
    Validates that the truck is not already on an active dispatch
    before creating.
    """
    try:
        waybill_exists = Dispatch.objects.filter(
            waybill_number=data.waybill_number
        ).exists()
        if waybill_exists:
            raise ConflictException(
                f"Waybill number '{data.waybill_number}' already exists"
            )

        logistics_officer = User.objects.get(email=created_by_id)
        # Enforce active dispatch lock on truck
        truck_locked = Dispatch.objects.filter(
            truck_id=data.truck_id,
            status__in=[
                Dispatch.Status.LOADING,
                Dispatch.Status.DISPATCHED,
                Dispatch.Status.IN_TRANSIT,
                Dispatch.Status.ARRIVED,
            ],
        ).exists()
        if truck_locked:
            raise BadRequestException(
                "This truck already has an active dispatch. "
                "It cannot be assigned until the current trip is completed."
            )

        dispatch = Dispatch.objects.create(
            waybill_number=data.waybill_number,
            sales_order_no=data.sales_order_no,
            truck_id=data.truck_id,
            driver_id=data.driver_id,
            customer_id=data.customer_id,
            delivery_address_id=data.delivery_address_id,
            origin_terminal_id=data.origin_terminal_id,
            route_id=data.route_id,
            product_id=data.product_id,
            quantity=data.quantity,
            expected_departure=data.expected_departure,
            notes=data.notes,
            organization_id=organization_id,
            created_by=logistics_officer,
        )

        _write_dispatch_status_log(
            dispatch=dispatch,
            previous_status=None,
            new_status=Dispatch.Status.PENDING,
            trigger_source=DispatchStatusLog.TriggerSource.MANUAL,
            triggered_by=logistics_officer,
            note="Dispatch created",
        )

        dispatch = _dispatch_qs().get(id=dispatch.id)

        # Compute ETA if origin terminal and delivery address have coordinates
        try:
            print("Starting the ETA Process...")
            from eta.predictor import compute_eta
            from terminals.models import Terminals
            from customers.models import DeliveryAddress
            from fleet.models import Product

            terminal     = None
            address      = None
            product_name = None

            if data.origin_terminal_id:
                try:
                    terminal = Terminals.objects.get(id=data.origin_terminal_id)
                except Terminals.DoesNotExist:
                    pass

            if data.delivery_address_id:
                try:
                    address = DeliveryAddress.objects.get(id=data.delivery_address_id)
                except DeliveryAddress.DoesNotExist:
                    pass

            if data.product_id:
                try:
                    product      = Product.objects.get(id=data.product_id)
                    product_name = product.name
                except Product.DoesNotExist:
                    pass

            if (
                terminal
                and address
                and terminal.latitude
                and terminal.longitude
                and address.latitude
                and address.longitude
            ):
                eta_result = compute_eta(
                    organization_id=organization_id,
                    origin_lat=terminal.latitude,
                    origin_lng=terminal.longitude,
                    dest_lat=address.latitude,
                    dest_lng=address.longitude,
                    expected_departure=data.expected_departure,
                    driver_id=data.driver_id,
                    origin_terminal_id=data.origin_terminal_id,
                    product_name=product_name,
                    quantity=float(data.quantity),
                )
                print(f"ETA RESULT: stage={eta_result['stage']} eta={eta_result['eta_datetime']} base={eta_result['base_eta_minutes']:.0f}min predicted={eta_result['predicted_minutes']:.0f}min")
                dispatch.eta = eta_result["eta_datetime"]
                dispatch.save(update_fields=["eta"])

                logger.info(
                    f"ETA computed for {dispatch.waybill_number}: "
                    f"Stage {eta_result['stage']} — "
                    f"{eta_result['eta_datetime']} "
                    f"(base: {eta_result['base_eta_minutes']:.0f}min "
                    f"predicted: {eta_result['predicted_minutes']:.0f}min)"
                )
            else:
                logger.warning(
                    f"ETA skipped for {dispatch.waybill_number} — missing coordinates. "
                    f"Terminal: {getattr(terminal, 'latitude', None)}/"
                    f"{getattr(terminal, 'longitude', None)} "
                    f"Address: {getattr(address, 'latitude', None)}/"
                    f"{getattr(address, 'longitude', None)}"
                )

        except Exception as eta_error:
            logger.error(
                f"ETA computation failed for {dispatch.waybill_number}: {eta_error}",
                exc_info=True,
            )
        return DispatchOutSchema.from_orm(dispatch)

    except (ConflictException, BadRequestException):
        raise
    except Exception as e:
        raise BadRequestException(str(e)) from e


def list_dispatches_service(
    organization_id: UUID,
    status: str | None = None,
    truck_id: UUID | None = None,
    customer_id: UUID | None = None,
) -> list[DispatchListOutSchema]:
    """
    Lists dispatches for an organization.
    Supports optional filtering by status, truck, or customer.
    """
    try:
        qs = Dispatch.objects.filter(
            organization_id=organization_id
        ).select_related(
            "truck", "driver", "customer", "product"
        ).order_by("-created_at")

        if status:
            qs = qs.filter(status=status)
        if truck_id:
            qs = qs.filter(truck_id=truck_id)
        if customer_id:
            qs = qs.filter(customer_id=customer_id)

        return [DispatchListOutSchema.from_orm(d) for d in qs]
    except Exception as e:
        raise BadRequestException(str(e)) from e


def get_dispatch_service(
    dispatch_id: UUID,
    organization_id: UUID,
) -> DispatchOutSchema:
    try:
        dispatch = _dispatch_qs().get(
            id=dispatch_id,
            organization_id=organization_id,
        )
        return DispatchOutSchema.from_orm(dispatch)
    except Dispatch.DoesNotExist:
        raise NotFoundException("Dispatch not found")
    except Exception as e:
        raise BadRequestException(str(e)) from e


def update_dispatch_service(
    dispatch_id: UUID,
    organization_id: UUID,
    data: DispatchUpdateSchema,
) -> DispatchOutSchema:
    """
    Updates a dispatch record.
    Only permitted while status is PENDING or LOADING.
    """
    try:
        dispatch = _dispatch_qs().get(
            id=dispatch_id,
            organization_id=organization_id,
        )

        if dispatch.status not in [
            Dispatch.Status.PENDING,
            Dispatch.Status.LOADING,
        ]:
            raise ForbiddenException(
                "Dispatch can only be updated while in Pending or Loading status"
            )

        update_data = data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(dispatch, field, value)
        dispatch.save()

        dispatch = _dispatch_qs().get(id=dispatch.id)
        return DispatchOutSchema.from_orm(dispatch)

    except (ForbiddenException, NotFoundException):
        raise
    except Dispatch.DoesNotExist:
        raise NotFoundException("Dispatch not found")
    except Exception as e:
        raise BadRequestException(str(e)) from e


def update_dispatch_status_service(
    dispatch_id: UUID,
    organization_id: UUID,
    data: DispatchStatusUpdateSchema,
    triggered_by: str,
) -> DispatchOutSchema:
    """
    Manually overrides a dispatch status.
    Writes a DispatchStatusLog entry for audit trail.
    """
    try:
        user = User.objects.get(email=triggered_by)
        dispatch = _dispatch_qs().get(
            id=dispatch_id,
            organization_id=organization_id,
        )

        previous_status = dispatch.status
        dispatch.status = data.status

        if data.status == Dispatch.Status.DISPATCHED:
            dispatch.actual_departure = timezone.now()

        if data.status == Dispatch.Status.IN_TRANSIT:
            dispatch.actual_departure = timezone.now()
            # Update truck status to outbound
            from fleet.models import Truck, TruckStatusLog
            truck = Truck.objects.get(id=dispatch.truck_id)
            previous_truck_status = truck.current_status
            truck.current_status = "outbound"
            truck.save()
            TruckStatusLog.objects.create(
                truck=truck,
                previous_status=previous_truck_status,
                new_status="outbound",
                trigger_source=TruckStatusLog.TriggerSource.MANUAL,
                triggered_by=user,
                note=f"Truck set to outbound via dispatch {dispatch.waybill_number}",
            )

        dispatch.save()

        _write_dispatch_status_log(
            dispatch=dispatch,
            previous_status=previous_status,
            new_status=data.status,
            trigger_source=DispatchStatusLog.TriggerSource.MANUAL,
            triggered_by=user,
            note=data.note,
        )

        dispatch = _dispatch_qs().get(id=dispatch.id)
        return DispatchOutSchema.from_orm(dispatch)

    except Dispatch.DoesNotExist:
        raise NotFoundException("Dispatch not found")
    except Exception as e:
        raise BadRequestException(str(e)) from e


def cancel_dispatch_service(
    dispatch_id: UUID,
    organization_id: UUID,
    triggered_by_id: UUID,
    note: str | None = None,
) -> DispatchOutSchema:
    """
    Cancels a dispatch.
    Only permitted while status is PENDING or LOADING.
    """
    try:
        dispatch = _dispatch_qs().get(
            id=dispatch_id,
            organization_id=organization_id,
        )

        if dispatch.status not in [
            Dispatch.Status.PENDING,
            Dispatch.Status.LOADING,
        ]:
            raise ForbiddenException(
                "Only pending or loading dispatches can be cancelled"
            )

        previous_status = dispatch.status
        dispatch.status = Dispatch.Status.CANCELLED
        dispatch.save()

        _write_dispatch_status_log(
            dispatch=dispatch,
            previous_status=previous_status,
            new_status=Dispatch.Status.CANCELLED,
            trigger_source=DispatchStatusLog.TriggerSource.MANUAL,
            triggered_by_id=triggered_by_id,
            note=note or "Dispatch cancelled",
        )

        dispatch = _dispatch_qs().get(id=dispatch.id)
        return DispatchOutSchema.from_orm(dispatch)

    except (ForbiddenException, NotFoundException):
        raise
    except Dispatch.DoesNotExist:
        raise NotFoundException("Dispatch not found")
    except Exception as e:
        raise BadRequestException(str(e)) from e


def driver_arrival_service(
    dispatch_id: UUID,
    organization_id: UUID,
) -> dict:
    """
    Called when driver signals arrival at customer site.
    Generates OTP and stores it on dispatch.
    Status remains IN_TRANSIT until customer confirms.
    Returns a simple message — not the full dispatch object.
    """
    try:
        dispatch = _dispatch_qs().get(
            id=dispatch_id,
            organization_id=organization_id,
        )

        if dispatch.status != Dispatch.Status.IN_TRANSIT:
            raise BadRequestException(
                "Driver arrival can only be signalled for in-transit dispatches"
            )

        otp = _generate_otp()

        dispatch.arrival_token = otp
        dispatch.arrival_token_expires_at = timezone.now() + timedelta(minutes=10)
        dispatch.arrival_token_attempts = 0
        # Status stays IN_TRANSIT — do NOT change to arrived here
        dispatch.save()

        _write_dispatch_status_log(
            dispatch=dispatch,
            previous_status=dispatch.status,
            new_status=dispatch.status,  # no status change
            trigger_source=DispatchStatusLog.TriggerSource.DRIVER,
            note="Driver signalled arrival — OTP generated and sent to customer",
        )

        # TODO: send OTP via SMS to customer primary contact

        return {
            "message": "Driver arrival registered. OTP sent to customer.",
            "dispatch_id": str(dispatch_id),
            "otp": otp,  # return in response for prototype testing
            "otp_expires_at": str(
                timezone.now() + timedelta(minutes=10)
            ),
        }

    except (BadRequestException, NotFoundException):
        raise
    except Dispatch.DoesNotExist:
        raise NotFoundException("Dispatch not found")
    except Exception as e:
        raise BadRequestException(str(e)) from e


def resend_otp_service(
    dispatch_id: UUID,
    organization_id: UUID,
) -> DispatchOutSchema:
    """
    Regenerates and resends OTP to customer.
    Only allowed while status is ARRIVED and previous OTP has expired.
    """
    try:
        dispatch = _dispatch_qs().get(
            id=dispatch_id,
            organization_id=organization_id,
        )

        if dispatch.status != Dispatch.Status.ARRIVED:
            raise BadRequestException(
                "OTP can only be resent for dispatches in Arrived status"
            )

        otp = _generate_otp()
        dispatch.arrival_token = otp
        dispatch.arrival_token_expires_at = timezone.now() + timedelta(minutes=10)
        dispatch.arrival_token_attempts = 0
        dispatch.save()

        # TODO: trigger SMS resend here
        # send_otp_sms(dispatch, otp)

        dispatch = _dispatch_qs().get(id=dispatch.id)
        return DispatchOutSchema.from_orm(dispatch)

    except (BadRequestException, NotFoundException):
        raise
    except Dispatch.DoesNotExist:
        raise NotFoundException("Dispatch not found")
    except Exception as e:
        raise BadRequestException(str(e)) from e


def confirm_delivery_service(
    dispatch_id: UUID,
    organization_id: UUID,
    data: DeliveryConfirmationCreateSchema,
) -> DeliveryConfirmationOutSchema:
    """
    Customer submits OTP and waybridge weight.
    Validates OTP, records delivery, computes variance.
    Status moves from IN_TRANSIT → DELIVERED on success.
    """
    try:
        dispatch = _dispatch_qs().get(
            id=dispatch_id,
            organization_id=organization_id,
        )

        if dispatch.status != Dispatch.Status.IN_TRANSIT:
            raise BadRequestException(
                "Delivery can only be confirmed for in-transit dispatches"
            )

        if not dispatch.arrival_token:
            raise BadRequestException(
                "No OTP has been generated for this dispatch. "
                "Driver must signal arrival first."
            )

        # Increment attempt before checking
        dispatch.arrival_token_attempts += 1
        dispatch.save(update_fields=["arrival_token_attempts"])

        if dispatch.arrival_token_attempts > 3:
            raise ForbiddenException(
                "Maximum OTP attempts exceeded. Request a new OTP."
            )

        if not dispatch.otp_is_valid:
            raise ForbiddenException(
                "OTP has expired. Request a new OTP."
            )

        if dispatch.arrival_token != data.otp:
            remaining = 3 - dispatch.arrival_token_attempts
            raise ForbiddenException(
                f"Incorrect OTP. {remaining} attempt(s) remaining."
            )

        # OTP valid — move to delivered
        previous_status = dispatch.status
        dispatch.status = Dispatch.Status.DELIVERED
        dispatch.actual_arrival = timezone.now()
        dispatch.arrival_token = None
        dispatch.arrival_token_expires_at = None
        dispatch.save()

        # Create delivery confirmation with variance
        confirmation = DeliveryConfirmation.objects.create(
            dispatch=dispatch,
            confirmed_by_name=data.confirmed_by_name,
            confirmed_by_phone=data.confirmed_by_phone,
            waybridge_weight=data.waybridge_weight,
        )

        _write_dispatch_status_log(
            dispatch=dispatch,
            previous_status=previous_status,
            new_status=Dispatch.Status.DELIVERED,
            trigger_source=DispatchStatusLog.TriggerSource.CUSTOMER,
            note=f"Delivery confirmed by {data.confirmed_by_name}. "
                        f"Waybridge: {data.waybridge_weight}",
        )

        # Update truck status to inbound
        from fleet.models import Truck, TruckStatusLog
        try:
            truck = Truck.objects.get(id=dispatch.truck_id)
            previous_truck_status = truck.current_status
            truck.current_status = "inbound"
            truck.save()
            TruckStatusLog.objects.create(
                truck=truck,
                previous_status=previous_truck_status,
                new_status="inbound",
                trigger_source=TruckStatusLog.TriggerSource.SYSTEM,
                note=f"Delivery confirmed — truck returning from "
                            f"{dispatch.waybill_number}",
            )
        except Truck.DoesNotExist:
            pass

        # Write ETA training record
        try:
            from eta.models import ETATripRecord
            actual_minutes = None
            if dispatch.actual_departure and confirmation.confirmed_at:
                delta = confirmation.confirmed_at - dispatch.actual_departure
                actual_minutes = delta.total_seconds() / 60

            if actual_minutes and actual_minutes > 0:
                ETATripRecord.objects.create(
                    dispatch=dispatch,
                    organization_id=organization_id,
                    distance_km=None,
                    base_eta_minutes=None,
                    hour_of_day=dispatch.actual_departure.hour,
                    day_of_week=dispatch.actual_departure.weekday(),
                    driver_id=dispatch.driver_id,
                    origin_terminal_id=dispatch.origin_terminal_id,
                    product_name=dispatch.product.name if dispatch.product else None,
                    quantity=float(dispatch.quantity),
                    actual_duration_minutes=actual_minutes,
                    departed_at=dispatch.actual_departure,
                    delivered_at=confirmation.confirmed_at,
                )
        except Exception as eta_err:
            import logging
            logging.getLogger(__name__).error(
                f"ETATripRecord creation failed: {eta_err}"
            )

        return DeliveryConfirmationOutSchema.from_orm(confirmation)

    except (BadRequestException, ForbiddenException, NotFoundException):
        raise
    except Dispatch.DoesNotExist:
        raise NotFoundException("Dispatch not found")
    except Exception as e:
        raise BadRequestException(str(e)) from e

# ── Trip Metadata services ─────────────────────────────────

def create_trip_metadata_service(
    dispatch_id: UUID,
    organization_id: UUID,
    data: TripMetadataCreateSchema,
) -> TripMetadataOutSchema:
    """
    Creates trip metadata for a dispatch.
    Fails if metadata already exists — use PATCH to update.
    """
    try:
        dispatch = Dispatch.objects.get(
            id=dispatch_id,
            organization_id=organization_id,
        )

        exists = TripMetadata.objects.filter(
            dispatch=dispatch
        ).exists()
        if exists:
            raise ConflictException(
                "Trip metadata already exists for this dispatch. Use PATCH to update."
            )

        metadata = TripMetadata.objects.create(
            dispatch=dispatch,
            **data.dict(exclude_unset=True),
        )
        return TripMetadataOutSchema.from_orm(metadata)

    except (ConflictException, NotFoundException):
        raise
    except Dispatch.DoesNotExist:
        raise NotFoundException("Dispatch not found")
    except Exception as e:
        raise BadRequestException(str(e)) from e


def get_trip_metadata_service(
    dispatch_id: UUID,
    organization_id: UUID,
) -> TripMetadataOutSchema:
    try:
        Dispatch.objects.get(
            id=dispatch_id,
            organization_id=organization_id,
        )
        metadata = TripMetadata.objects.get(dispatch_id=dispatch_id)
        return TripMetadataOutSchema.from_orm(metadata)
    except Dispatch.DoesNotExist:
        raise NotFoundException("Dispatch not found")
    except TripMetadata.DoesNotExist:
        raise NotFoundException("Trip metadata not found")
    except Exception as e:
        raise BadRequestException(str(e)) from e


def update_trip_metadata_service(
    dispatch_id: UUID,
    organization_id: UUID,
    data: TripMetadataUpdateSchema,
) -> TripMetadataOutSchema:
    try:
        Dispatch.objects.get(
            id=dispatch_id,
            organization_id=organization_id,
        )
        metadata = TripMetadata.objects.get(dispatch_id=dispatch_id)
        for field, value in data.dict(exclude_unset=True).items():
            setattr(metadata, field, value)
        metadata.save()
        return TripMetadataOutSchema.from_orm(metadata)
    except Dispatch.DoesNotExist:
        raise NotFoundException("Dispatch not found")
    except TripMetadata.DoesNotExist:
        raise NotFoundException("Trip metadata not found")
    except Exception as e:
        raise BadRequestException(str(e)) from e
