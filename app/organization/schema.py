from ninja import ModelSchema, Schema

from organization.models import Organizations, OrganizationSettings
from uuid import UUID
from typing import Optional
from datetime import datetime

class OrganizationOutSchema(ModelSchema):
    class Meta:
        model = Organizations
        fields = "__all__"


class OrganizationCreateSchema(ModelSchema):
    class Meta:
        model = Organizations
        fields = ["name", "slug", "industry"]


class OrganizationUpdateSchema(ModelSchema):
    class Meta:
        model = Organizations
        fields = ["name", "slug", "industry", "is_active"]

class OrganizationOrgAdminUpdateSchema(ModelSchema):
    """
    Restricted update — org admin can only edit these fields.
    Cannot change slug, is_active, or industry.
    """
    class Meta:
        model = Organizations
        fields = ["name", "industry"]


class OrganizationSettingsUpdateSchema(ModelSchema):
    class Meta:
        model = OrganizationSettings
        fields = ["time_zone", "language"]


class OrganizationSettingsOutSchema(ModelSchema):
    class Meta:
        model = OrganizationSettings
        fields = "__all__"
