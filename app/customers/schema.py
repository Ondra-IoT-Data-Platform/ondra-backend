from typing import List, Optional
from uuid import UUID

from ninja import ModelSchema, Schema

from customers.models import Customer, CustomerContact, DeliveryAddress


class CustomerContactCreateSchema(Schema):
    """Creates a contact for a customer."""
    full_name: str
    phone_number: str
    email: Optional[str] = None
    job_title: Optional[str] = None
    is_primary: bool = False


class CustomerContactUpdateSchema(Schema):
    """Partially updates a customer contact."""
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    email: Optional[str] = None
    job_title: Optional[str] = None
    is_primary: Optional[bool] = None
    is_active: Optional[bool] = None


class CustomerContactOutSchema(ModelSchema):
    """Customer contact output."""
    class Meta:
        model = CustomerContact
        fields = [
            "id", "customer", "full_name", "phone_number",
            "email", "job_title", "is_primary",
            "is_active", "created_at", "updated_at",
        ]


class DeliveryAddressCreateSchema(Schema):
    """Creates a delivery address for a customer."""
    label: str
    address: str
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    is_default: bool = False


class DeliveryAddressUpdateSchema(Schema):
    """Partially updates a delivery address."""
    label: Optional[str] = None
    address: Optional[str] = None
    latitude: Optional[str] = None
    longitude: Optional[str] = None
    is_default: Optional[bool] = None
    is_active: Optional[bool] = None


class DeliveryAddressOutSchema(ModelSchema):
    """Delivery address output."""
    class Meta:
        model = DeliveryAddress
        fields = [
            "id", "customer", "label", "address",
            "latitude", "longitude", "is_default",
            "is_active", "created_at", "updated_at",
        ]


class CustomerCreateSchema(Schema):
    """Creates a new customer."""
    name: str
    email: Optional[str] = None
    phone_number: Optional[str] = None
    erp_code: Optional[str] = None
    address: Optional[str] = None


class CustomerUpdateSchema(Schema):
    """Partially updates a customer."""
    name: Optional[str] = None
    email: Optional[str] = None
    phone_number: Optional[str] = None
    erp_code: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


class CustomerOutSchema(ModelSchema):
    """Customer list output."""
    class Meta:
        model = Customer
        fields = [
            "id", "name", "email", "phone_number",
            "erp_code", "address", "is_active",
            "organization", "created_at", "updated_at",
        ]


class CustomerDetailOutSchema(CustomerOutSchema):
    """Full customer detail including contacts and delivery addresses."""
    contacts: List[CustomerContactOutSchema] = []
    delivery_addresses: List[DeliveryAddressOutSchema] = []
