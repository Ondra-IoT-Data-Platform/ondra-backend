# customers/services.py
from uuid import UUID

from config.exceptions import (
    BadRequestException,
    ConflictException,
    NotFoundException,
)
from customers.models import Customer, CustomerContact, DeliveryAddress
from customers.schema import (
    CustomerContactCreateSchema,
    CustomerContactOutSchema,
    CustomerContactUpdateSchema,
    CustomerCreateSchema,
    CustomerDetailOutSchema,
    CustomerOutSchema,
    CustomerUpdateSchema,
    DeliveryAddressCreateSchema,
    DeliveryAddressOutSchema,
    DeliveryAddressUpdateSchema,
)


def _customer_qs():
    return Customer.objects.select_related("organization")


# ── Customer services ──────────────────────────────────────

def create_customer_service(
    data: CustomerCreateSchema,
    organization_id: UUID,
) -> CustomerOutSchema:
    try:
        exists = Customer.objects.filter(
            name=data.name,
            organization_id=organization_id,
        ).exists()
        if exists:
            raise ConflictException(
                f"Customer '{data.name}' already exists in this organization"
            )

        customer = Customer.objects.create(
            **data.dict(exclude_unset=True),
            organization_id=organization_id,
        )
        customer = _customer_qs().get(id=customer.id)
        return CustomerOutSchema.from_orm(customer)
    except ConflictException:
        raise
    except Exception as e:
        raise BadRequestException(str(e)) from e


def list_customers_service(
    organization_id: UUID,
) -> list[CustomerOutSchema]:
    try:
        qs = _customer_qs().filter(
            organization_id=organization_id
        ).order_by("name")
        return [CustomerOutSchema.from_orm(c) for c in qs]
    except Exception as e:
        raise BadRequestException(str(e)) from e


def get_customer_service(
    customer_id: UUID,
    organization_id: UUID,
) -> CustomerOutSchema:
    try:
        customer = _customer_qs().get(
            id=customer_id,
            organization_id=organization_id,
        )
        return CustomerOutSchema.from_orm(customer)
    except Customer.DoesNotExist:
        raise NotFoundException("Customer not found")
    except Exception as e:
        raise BadRequestException(str(e)) from e


def get_customer_detail_service(
    customer_id: UUID,
    organization_id: UUID,
) -> CustomerDetailOutSchema:
    try:
        customer = _customer_qs().get(
            id=customer_id,
            organization_id=organization_id,
        )
        contacts = [
            CustomerContactOutSchema.from_orm(c)
            for c in CustomerContact.objects.filter(customer=customer)
        ]
        addresses = [
            DeliveryAddressOutSchema.from_orm(a)
            for a in DeliveryAddress.objects.filter(customer=customer)
        ]
        return CustomerDetailOutSchema(
            id=customer.id,
            name=customer.name,
            email=customer.email,
            phone_number=customer.phone_number,
            erp_code=customer.erp_code,
            address=customer.address,
            is_active=customer.is_active,
            organization=customer.organization_id,
            created_at=customer.created_at,
            updated_at=customer.updated_at,
            contacts=contacts,
            delivery_addresses=addresses,
        )
    except Customer.DoesNotExist:
        raise NotFoundException("Customer not found")
    except Exception as e:
        raise BadRequestException(str(e)) from e


def update_customer_service(
    customer_id: UUID,
    organization_id: UUID,
    data: CustomerUpdateSchema,
) -> CustomerOutSchema:
    try:
        customer = _customer_qs().get(
            id=customer_id,
            organization_id=organization_id,
        )
        for field, value in data.dict(exclude_unset=True).items():
            setattr(customer, field, value)
        customer.save()
        customer = _customer_qs().get(id=customer.id)
        return CustomerOutSchema.from_orm(customer)
    except Customer.DoesNotExist:
        raise NotFoundException("Customer not found")
    except Exception as e:
        raise BadRequestException(str(e)) from e


def deactivate_customer_service(
    customer_id: UUID,
    organization_id: UUID,
) -> None:
    try:
        customer = Customer.objects.get(
            id=customer_id,
            organization_id=organization_id,
        )
        customer.is_active = False
        customer.save()
    except Customer.DoesNotExist:
        raise NotFoundException("Customer not found")
    except Exception as e:
        raise BadRequestException(str(e)) from e


# ── Customer Contact services ──────────────────────────────

def create_customer_contact_service(
    customer_id: UUID,
    organization_id: UUID,
    data: CustomerContactCreateSchema,
) -> CustomerContactOutSchema:
    try:
        customer = Customer.objects.get(
            id=customer_id,
            organization_id=organization_id,
        )
        if data.is_primary:
            CustomerContact.objects.filter(
                customer=customer, is_primary=True
            ).update(is_primary=False)

        contact = CustomerContact.objects.create(
            customer=customer,
            **data.dict(exclude_unset=True),
        )
        return CustomerContactOutSchema.from_orm(contact)
    except Customer.DoesNotExist:
        raise NotFoundException("Customer not found")
    except Exception as e:
        raise BadRequestException(str(e)) from e


def update_customer_contact_service(
    contact_id: UUID,
    customer_id: UUID,
    organization_id: UUID,
    data: CustomerContactUpdateSchema,
) -> CustomerContactOutSchema:
    try:
        customer = Customer.objects.get(
            id=customer_id,
            organization_id=organization_id,
        )
        contact = CustomerContact.objects.get(
            id=contact_id,
            customer=customer,
        )
        if data.is_primary:
            CustomerContact.objects.filter(
                customer=customer, is_primary=True
            ).exclude(id=contact_id).update(is_primary=False)

        for field, value in data.dict(exclude_unset=True).items():
            setattr(contact, field, value)
        contact.save()
        return CustomerContactOutSchema.from_orm(contact)
    except Customer.DoesNotExist:
        raise NotFoundException("Customer not found")
    except CustomerContact.DoesNotExist:
        raise NotFoundException("Contact not found")
    except Exception as e:
        raise BadRequestException(str(e)) from e


def delete_customer_contact_service(
    contact_id: UUID,
    customer_id: UUID,
    organization_id: UUID,
) -> None:
    try:
        customer = Customer.objects.get(
            id=customer_id,
            organization_id=organization_id,
        )
        contact = CustomerContact.objects.get(
            id=contact_id,
            customer=customer,
        )
        contact.delete()
    except Customer.DoesNotExist:
        raise NotFoundException("Customer not found")
    except CustomerContact.DoesNotExist:
        raise NotFoundException("Contact not found")
    except Exception as e:
        raise BadRequestException(str(e)) from e


# ── Delivery Address services ──────────────────────────────

def create_delivery_address_service(
    customer_id: UUID,
    organization_id: UUID,
    data: DeliveryAddressCreateSchema,
) -> DeliveryAddressOutSchema:
    try:
        customer = Customer.objects.get(
            id=customer_id,
            organization_id=organization_id,
        )
        if data.is_default:
            DeliveryAddress.objects.filter(
                customer=customer, is_default=True
            ).update(is_default=False)

        address = DeliveryAddress.objects.create(
            customer=customer,
            **data.dict(exclude_unset=True),
        )
        return DeliveryAddressOutSchema.from_orm(address)
    except Customer.DoesNotExist:
        raise NotFoundException("Customer not found")
    except Exception as e:
        raise BadRequestException(str(e)) from e


def update_delivery_address_service(
    address_id: UUID,
    customer_id: UUID,
    organization_id: UUID,
    data: DeliveryAddressUpdateSchema,
) -> DeliveryAddressOutSchema:
    try:
        customer = Customer.objects.get(
            id=customer_id,
            organization_id=organization_id,
        )
        address = DeliveryAddress.objects.get(
            id=address_id,
            customer=customer,
        )
        if data.is_default:
            DeliveryAddress.objects.filter(
                customer=customer, is_default=True
            ).exclude(id=address_id).update(is_default=False)

        for field, value in data.dict(exclude_unset=True).items():
            setattr(address, field, value)
        address.save()
        return DeliveryAddressOutSchema.from_orm(address)
    except Customer.DoesNotExist:
        raise NotFoundException("Customer not found")
    except DeliveryAddress.DoesNotExist:
        raise NotFoundException("Delivery address not found")
    except Exception as e:
        raise BadRequestException(str(e)) from e


def delete_delivery_address_service(
    address_id: UUID,
    customer_id: UUID,
    organization_id: UUID,
) -> None:
    try:
        customer = Customer.objects.get(
            id=customer_id,
            organization_id=organization_id,
        )
        address = DeliveryAddress.objects.get(
            id=address_id,
            customer=customer,
        )
        address.delete()
    except Customer.DoesNotExist:
        raise NotFoundException("Customer not found")
    except DeliveryAddress.DoesNotExist:
        raise NotFoundException("Delivery address not found")
    except Exception as e:
        raise BadRequestException(str(e)) from e
