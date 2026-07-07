from datetime import datetime
from typing import Optional
from uuid import UUID

from ninja import ModelSchema, Schema

from users.models import DriverProfile, OfficeProfile, Role, User


# ── User schemas ───────────────────────────────────────────

class UserCreateSchema(Schema):
    """Creates a new user. Password is hashed in the service layer."""
    email: str
    password: str
    role_id: int


class UserUpdateSchema(ModelSchema):
    """Updates email or active status. Role and organization changes are separate endpoints."""
    class Meta:
        model = User
        fields = ["email", "is_active"]
        fields_optional = "__all__"


class UserRoleUpdateSchema(Schema):
    """Changes a user's assigned role."""
    role_id: int


class UserOutSchema(ModelSchema):
    """Safe user output. Excludes password and internal permission fields."""
    role_name: Optional[str] = None

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "is_active",
            "organization",
            "role",
            "created_at",
            "updated_at",
        ]

    @staticmethod
    def resolve_role_name(obj) -> Optional[str]:
        return obj.role.name if obj.role else None


class UserWithProfileOutSchema(Schema):
    """Full user detail including office or driver profile."""
    id: UUID
    email: str
    is_active: bool
    organization_id: UUID
    role_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    office_profile: Optional["OfficeProfileOutSchema"] = None
    driver_profile: Optional["DriverProfileOutSchema"] = None


# ── Role schema ────────────────────────────────────────────

class RoleOutSchema(ModelSchema):
    """Role output scoped to an organization."""
    class Meta:
        model = Role
        fields = ["id", "name", "organization", "created_at"]


# ── Office profile schemas ─────────────────────────────────

class OfficeProfileCreateSchema(ModelSchema):
    """Creates an office profile for non-driver users. Display photo is handled separately."""
    class Meta:
        model = OfficeProfile
        fields = ["full_name", "job_title", "phone_number"]
        fields_optional = ["job_title", "phone_number"]


class OfficeProfileUpdateSchema(ModelSchema):
    """Partially updates an office profile."""
    class Meta:
        model = OfficeProfile
        fields = ["full_name", "job_title", "phone_number"]
        fields_optional = "__all__"


class OfficeProfileOutSchema(ModelSchema):
    """Office profile output."""
    class Meta:
        model = OfficeProfile
        fields = [
            "id",
            "full_name",
            "job_title",
            "phone_number",
            "created_at",
            "updated_at",
        ]


# ── Driver profile schemas ─────────────────────────────────

class DriverProfileCreateSchema(ModelSchema):
    """Creates a driver profile for users with the Driver role."""
    class Meta:
        model = DriverProfile
        fields = ["full_name", "license_number", "ops_location", "phone_number"]
        fields_optional = ["license_number", "ops_location", "phone_number"]


class DriverProfileUpdateSchema(ModelSchema):
    """Partially updates a driver profile."""
    class Meta:
        model = DriverProfile
        fields = ["full_name", "license_number", "ops_location", "phone_number"]
        fields_optional = "__all__"


class DriverProfileOutSchema(ModelSchema):
    """Driver profile output."""
    class Meta:
        model = DriverProfile
        fields = [
            "id",
            "full_name",
            "license_number",
            "ops_location",
            "phone_number",
            "created_at",
            "updated_at",
        ]


UserWithProfileOutSchema.model_rebuild()
