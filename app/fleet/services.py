from uuid import UUID

from config.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
)
from fleet.models import Product, Route, Truck, TruckLocation, TruckStatusLog
from fleet.schema import (
    ProductCreateSchema,
    ProductOutSchema,
    ProductUpdateSchema,
    RouteCreateSchema,
    RouteOutSchema,
    RouteUpdateSchema,
    TruckCreateSchema,
    TruckLocationOutSchema,
    TruckOutSchema,
    TruckStatusLogOutSchema,
    TruckStatusUpdateSchema,
    TruckUpdateSchema,
)


# ── Product services ───────────────────────────────────────

async def create_product_service(
    data: ProductCreateSchema,
    organization_id: UUID,
) -> ProductOutSchema:
    try:
        exists = await Product.objects.filter(
            name=data.name,
            organization_id=organization_id,
        ).aexists()
        if exists:
            raise ConflictException(
                f"Product '{data.name}' already exists in this organization"
            ) from None

        product = await Product.objects.acreate(
            **data.dict(exclude_unset=True),
            organization_id=organization_id,
        )
        return ProductOutSchema.from_orm(product)
    except ConflictException:
        raise
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def list_products_service(
    organization_id: UUID,
) -> list[ProductOutSchema]:
    try:
        products = Product.objects.filter(
            organization_id=organization_id
        ).order_by("name")
        return [ProductOutSchema.from_orm(p) async for p in products]
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def get_product_service(
    product_id: UUID,
    organization_id: UUID,
) -> ProductOutSchema:
    try:
        product = await Product.objects.aget(
            id=product_id,
            organization_id=organization_id,
        )
        return ProductOutSchema.from_orm(product)
    except Product.DoesNotExist:
        raise NotFoundException("Product not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def update_product_service(
    product_id: UUID,
    organization_id: UUID,
    data: ProductUpdateSchema,
) -> ProductOutSchema:
    try:
        product = await Product.objects.aget(
            id=product_id,
            organization_id=organization_id,
        )
        for field, value in data.dict(exclude_unset=True).items():
            setattr(product, field, value)
        await product.asave()
        return ProductOutSchema.from_orm(product)
    except Product.DoesNotExist:
        raise NotFoundException("Product not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


# ── Route services ─────────────────────────────────────────

async def create_route_service(
    data: RouteCreateSchema,
    organization_id: UUID,
) -> RouteOutSchema:
    try:
        exists = await Route.objects.filter(
            route_name=data.route_name,
            organization_id=organization_id,
        ).aexists()
        if exists:
            raise ConflictException(
                f"Route '{data.route_name}' already exists"
            ) from None

        route = await Route.objects.acreate(
            **data.dict(exclude_unset=True),
            organization_id=organization_id,
        )
        return RouteOutSchema.from_orm(route)
    except ConflictException:
        raise
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def list_routes_service(
    organization_id: UUID,
) -> list[RouteOutSchema]:
    try:
        routes = Route.objects.filter(
            organization_id=organization_id
        ).select_related("origin_terminal").order_by("route_name")
        return [RouteOutSchema.from_orm(r) async for r in routes]
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def get_route_service(
    route_id: UUID,
    organization_id: UUID,
) -> RouteOutSchema:
    try:
        route = await Route.objects.select_related(
            "origin_terminal"
        ).aget(id=route_id, organization_id=organization_id)
        return RouteOutSchema.from_orm(route)
    except Route.DoesNotExist:
        raise NotFoundException("Route not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def update_route_service(
    route_id: UUID,
    organization_id: UUID,
    data: RouteUpdateSchema,
) -> RouteOutSchema:
    try:
        route = await Route.objects.aget(
            id=route_id,
            organization_id=organization_id,
        )
        for field, value in data.dict(exclude_unset=True).items():
            setattr(route, field, value)
        await route.asave()
        return RouteOutSchema.from_orm(route)
    except Route.DoesNotExist:
        raise NotFoundException("Route not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def delete_route_service(
    route_id: UUID,
    organization_id: UUID,
) -> None:
    try:
        route = await Route.objects.aget(
            id=route_id,
            organization_id=organization_id,
        )
        await route.adelete()
    except Route.DoesNotExist:
        raise NotFoundException("Route not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


# ── Truck services ─────────────────────────────────────────

async def create_truck_service(
    data: TruckCreateSchema,
    organization_id: UUID,
) -> TruckOutSchema:
    try:
        exists = await Truck.objects.filter(
            plate_number=data.plate_number
        ).aexists()
        if exists:
            raise ConflictException(
                f"Truck '{data.plate_number}' is already registered"
            ) from None

        truck = await Truck.objects.acreate(
            **data.dict(exclude_unset=True),
            organization_id=organization_id,
        )
        truck = await Truck.objects.select_related(
            "default_product", "home_terminal", "location"
        ).aget(id=truck.id)
        return TruckOutSchema.from_orm(truck)
    except ConflictException:
        raise
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def list_trucks_service(
    organization_id: UUID,
    status: str | None = None,
) -> list[TruckOutSchema]:
    try:
        qs = Truck.objects.filter(
            organization_id=organization_id
        ).select_related(
            "default_product", "home_terminal", "location"
        ).order_by("plate_number")

        if status:
            qs = qs.filter(current_status=status)

        return [TruckOutSchema.from_orm(t) async for t in qs]
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def get_truck_service(
    truck_id: UUID,
    organization_id: UUID,
) -> TruckOutSchema:
    try:
        truck = await Truck.objects.select_related(
            "default_product", "home_terminal", "location"
        ).aget(id=truck_id, organization_id=organization_id)
        return TruckOutSchema.from_orm(truck)
    except Truck.DoesNotExist:
        raise NotFoundException("Truck not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def update_truck_service(
    truck_id: UUID,
    organization_id: UUID,
    data: TruckUpdateSchema,
) -> TruckOutSchema:
    try:
        truck = await Truck.objects.select_related(
            "default_product", "home_terminal", "location"
        ).aget(id=truck_id, organization_id=organization_id)

        for field, value in data.dict(exclude_unset=True).items():
            setattr(truck, field, value)
        await truck.asave()

        truck = await Truck.objects.select_related(
            "default_product", "home_terminal", "location"
        ).aget(id=truck.id)
        return TruckOutSchema.from_orm(truck)
    except Truck.DoesNotExist:
        raise NotFoundException("Truck not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def update_truck_status_service(
    truck_id: UUID,
    organization_id: UUID,
    data: TruckStatusUpdateSchema,
    triggered_by_id: UUID,
) -> TruckOutSchema:
    """
    Manual truck status override.
    Writes a TruckStatusLog entry for audit trail.
    """
    try:
        truck = await Truck.objects.select_related(
            "default_product", "home_terminal", "location"
        ).aget(id=truck_id, organization_id=organization_id)

        previous_status = truck.current_status
        truck.current_status = data.status
        await truck.asave()

        await TruckStatusLog.objects.acreate(
            truck=truck,
            previous_status=previous_status,
            new_status=data.status,
            trigger_source=TruckStatusLog.TriggerSource.MANUAL,
            triggered_by_id=triggered_by_id,
            note=data.note,
        )

        truck = await Truck.objects.select_related(
            "default_product", "home_terminal", "location"
        ).aget(id=truck.id)
        return TruckOutSchema.from_orm(truck)
    except Truck.DoesNotExist:
        raise NotFoundException("Truck not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def get_truck_status_history_service(
    truck_id: UUID,
    organization_id: UUID,
) -> list[TruckStatusLogOutSchema]:
    """Returns the full status change history for a truck."""
    try:
        await Truck.objects.aget(
            id=truck_id,
            organization_id=organization_id,
        )
        logs = TruckStatusLog.objects.filter(
            truck_id=truck_id
        ).select_related(
            "triggered_by"
        ).order_by("-created_at")
        return [TruckStatusLogOutSchema.from_orm(log) async for log in logs]
    except Truck.DoesNotExist:
        raise NotFoundException("Truck not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def deactivate_truck_service(
    truck_id: UUID,
    organization_id: UUID,
) -> None:
    try:
        truck = await Truck.objects.aget(
            id=truck_id,
            organization_id=organization_id,
        )
        truck.is_active = False
        truck.current_status = Truck.StatusChoices.DECOMMISSIONED
        await truck.asave()
    except Truck.DoesNotExist:
        raise NotFoundException("Truck not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e
