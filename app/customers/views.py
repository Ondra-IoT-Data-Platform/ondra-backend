# customers/views.py
from uuid import UUID

from ninja import Router

from access.auth_utils import JWTAuthBearer
from config.exceptions import (
    BadRequestException,
    ConflictException,
    ForbiddenException,
    NotFoundException,
)
from config.permissions import require_roles
from config.schema import StatusCode, create_response, BaseResponseSchema
from customers.schema import (
    CustomerContactCreateSchema,
    CustomerContactUpdateSchema,
    CustomerCreateSchema,
    CustomerUpdateSchema,
    DeliveryAddressCreateSchema,
    DeliveryAddressUpdateSchema,
)
from customers.services import (
    create_customer_contact_service,
    create_customer_service,
    create_delivery_address_service,
    deactivate_customer_service,
    delete_customer_contact_service,
    delete_delivery_address_service,
    get_customer_detail_service,
    get_customer_service,
    list_customers_service,
    update_customer_contact_service,
    update_customer_service,
    update_delivery_address_service,
)
from organization.models import OrganizationMember


R = OrganizationMember.RoleChoices


router = Router(tags=["Customers"], auth=JWTAuthBearer())

CUSTOMER_MANAGERS = [R.ORG_ADMIN, R.MANAGEMENT, R.LOGISTICS_OFFICER, R.SALES]
CUSTOMER_VIEWERS = [
    R.ORG_ADMIN, R.MANAGEMENT, R.LOGISTICS_OFFICER,
    R.TRACKING_OFFICER, R.SALES,
]


# ── Customer endpoints ─────────────────────────────────────

@router.post("/organization/{org_id}/customers")
@require_roles(*CUSTOMER_MANAGERS)
def create_customer(request, org_id: UUID, data: CustomerCreateSchema) -> BaseResponseSchema:
    try:
        result = create_customer_service(data, org_id)
        return create_response(status_code=StatusCode.CREATED, data=result)
    except ConflictException as e:
        raise ConflictException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/organization/{org_id}/customers")
@require_roles(*CUSTOMER_VIEWERS)
def list_customers(request, org_id: UUID) -> dict:
    try:
        result = list_customers_service(org_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/organization/{org_id}/customers/{customer_id}")
@require_roles(*CUSTOMER_VIEWERS)
def get_customer(request, org_id: UUID, customer_id: UUID) -> dict:
    try:
        result = get_customer_service(customer_id, org_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.get("/organization/{org_id}/customers/{customer_id}/detail")
@require_roles(*CUSTOMER_VIEWERS)
def get_customer_detail(request, org_id: UUID, customer_id: UUID) -> dict:
    """Returns customer with nested contacts and delivery addresses."""
    try:
        result = get_customer_detail_service(customer_id, org_id)
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.patch("/organization/{org_id}/customers/{customer_id}")
@require_roles(*CUSTOMER_MANAGERS)
def update_customer(
    request, org_id: UUID, customer_id: UUID, data: CustomerUpdateSchema
) -> dict:
    try:
        org_id = request.auth.get("org_id")
        result = update_customer_service(customer_id, org_id, data)
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.delete("/customers/{customer_id}")
@require_roles(R.ORG_ADMIN, R.MANAGEMENT)
def deactivate_customer(request, customer_id: UUID) -> dict:
    try:
        org_id = request.auth.get("org_id")
        deactivate_customer_service(customer_id, org_id)
        return create_response(
            status_code=StatusCode.NO_CONTENT,
            message="Customer deactivated successfully.",
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


# ── Customer Contact endpoints ─────────────────────────────

@router.post("/organization/{org_id}/customers/{customer_id}/contacts")
@require_roles(*CUSTOMER_MANAGERS)
def create_customer_contact(
    request, org_id: UUID, customer_id: UUID, data: CustomerContactCreateSchema
) -> dict:
    try:
        result = create_customer_contact_service(
            customer_id, org_id, data
        )
        return create_response(status_code=StatusCode.CREATED, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.patch("/organization/{org_id}/customers/{customer_id}/contacts/{contact_id}")
@require_roles(*CUSTOMER_MANAGERS)
def update_customer_contact(
    request,
    org_id: UUID,
    customer_id: UUID,
    contact_id: UUID,
    data: CustomerContactUpdateSchema,
) -> dict:
    try:
        result = update_customer_contact_service(
            contact_id, customer_id, org_id, data
        )
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.delete("/organization/{org_id}/customers/{customer_id}/contacts/{contact_id}")
@require_roles(R.ORG_ADMIN, R.MANAGEMENT)
def delete_customer_contact(
    request,  org_id: UUID, customer_id: UUID, contact_id: UUID
) -> dict:
    try:
        delete_customer_contact_service(
            contact_id, customer_id, org_id
        )
        return create_response(
            status_code=StatusCode.NO_CONTENT,
            message="Contact deleted successfully.",
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


# ── Delivery Address endpoints ─────────────────────────────

@router.post("/organization/{org_id}/customers/{customer_id}/addresses")
@require_roles(*CUSTOMER_MANAGERS)
def create_delivery_address(
    request, org_id: UUID, customer_id: UUID, data: DeliveryAddressCreateSchema
) -> dict:
    try:
        result = create_delivery_address_service(
            customer_id, org_id, data
        )
        return create_response(status_code=StatusCode.CREATED, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.patch("/organization/{org_id}/customers/{customer_id}/addresses/{address_id}")
@require_roles(*CUSTOMER_MANAGERS)
def update_delivery_address(
    request,
    org_id: UUID,
    customer_id: UUID,
    address_id: UUID,
    data: DeliveryAddressUpdateSchema,
) -> dict:
    try:
        result = update_delivery_address_service(
            address_id, customer_id, org_id, data
        )
        return create_response(status_code=StatusCode.OK, data=result)
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e


@router.delete("/organization/{org_id}/customers/{customer_id}/addresses/{address_id}")
@require_roles(R.ORG_ADMIN, R.MANAGEMENT)
def delete_delivery_address(
    request, org_id: UUID, customer_id: UUID, address_id: UUID
) -> dict:
    try:
        delete_delivery_address_service(
            address_id, customer_id, org_id
        )
        return create_response(
            status_code=StatusCode.NO_CONTENT,
            message="Delivery address deleted successfully.",
        )
    except NotFoundException as e:
        raise NotFoundException(str(e)) from e
    except BadRequestException as e:
        raise BadRequestException(str(e)) from e
