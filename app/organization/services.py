
##################################################
# ----------- ADMIN PRIVILEGE FOR NOW -------
##################################################


from uuid import UUID
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async
# from users.schema import RoleOutSchema

from config.exceptions import (
    InternalServerErrorException,
    BadRequestException,
    NotFoundException,
    ForbiddenException,
    ConflictException
)
from organization.schema import (
    OrganizationCreateSchema,
    OrganizationUpdateSchema,
    OrganizationOrgAdminUpdateSchema,
    OrganizationOutSchema,
    OrganizationSettingsUpdateSchema,
    OrganizationSettingsOutSchema,
    OrganizationMembersSchema
)
from organization.models import Organizations, OrganizationMember, OrganizationSettings


User = get_user_model()



def list_user_roles_service(organization_id: UUID) -> list[dict]:
    """
    Lists all available roles for an organization in a format suitable for forms.
    Returns roles with value and label for dropdown selection.
    """
    try:
        # Validate organization exists
        if not Organizations.objects.filter(id=organization_id, is_active=True).exists():
            raise NotFoundException("Organization not found")

        # Get all role choices from the model
        roles = []
        for role_value, role_label in OrganizationMember.RoleChoices.choices:
            roles.append({
                "value": role_value,
                "label": role_label
            })

        return roles

    except NotFoundException:
        raise
    except Exception as e:
        raise BadRequestException(f"Failed to list roles: {str(e)}") from e




def create_organization_service(
    data: OrganizationCreateSchema,
) -> OrganizationOutSchema:
    """
    Creates a new organization.
    Superuser only.
    Seeds all 8 roles automatically after creation.
    """
    try:
        print("Attempting to filter org by slug")
        exists = Organizations.objects.filter(
            slug=data.slug
        )

        if exists:

            raise ConflictException(
                f"Organization with slug '{data.slug}' already exists"
            ) from None

        org_data = data.model_dump()
        org =   Organizations.objects.create(**org_data)


        # Seed roles for the new organization
        # a _seed_org_roles(org)

        return OrganizationOutSchema.model_validate(org)
    except ConflictException:
        raise
    except Exception as e:
        # if "already exists" in str(e).lower() or "conflict" in type(e).__name__.lower():
        #     raise
        raise InternalServerErrorException(str(e)) from e



# async def _seed_org_roles(org: Organizations) -> None:
#     """Seeds all 8 default roles for a new organization."""
#     from users.models import Role

#     for role_name, _ in Role.RoleName.choices:
#         await Role.objects.aget_or_create(
#             name=role_name,
#             organization=org
#         )


def list_organization_members_service(organization_id: UUID) -> list[OrganizationMembersSchema]:
    """
    Lists all members of an organization.
    Superuser can list any org's members.
    Org admin can only list their own org's members.
    """
    try:
        members = OrganizationMember.objects.filter(
            organization_id=organization_id
        ).select_related("user", "role")

        return [
            OrganizationMembersSchema.from_orm(member)
            for member in members
        ]
    except Exception as e:
        raise BadRequestException(str(e)) from e



def list_organizations_service() -> list[OrganizationOutSchema]:
    """
    Lists all organizations.
    Superuser only.
    """
    try:
        # Get organizations as a list
        orgs = list(Organizations.objects.filter(is_active=True).order_by("name"))
        # Convert each organization to schema using from_orm
        return [OrganizationOutSchema.model_validate(org) for org in orgs]

    except Exception as e:
        raise BadRequestException(str(e)) from e


def get_organization_service(
    org_id: UUID,
) -> OrganizationOutSchema:
    """
    Retrieves a single organization.
    Superuser can get any org.
    Org admin can only get their own org.
    """
    try:
        org = Organizations.objects.get(id=org_id)
        return OrganizationOutSchema.model_validate(org)
    except Organizations.DoesNotExist:
        raise NotFoundException("Organization not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


def update_organization_service(
    org_id: UUID,
    data: OrganizationUpdateSchema,
) -> OrganizationOutSchema:
    """
    Full update — superuser only.
    Can update any field including is_active and slug.
    """
    try:
        org = Organizations.objects.get(id=org_id)
        update_data = data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(org, field, value)
        org.save()
        return OrganizationOutSchema.model_validate(org)
    except Organizations.DoesNotExist:
        raise NotFoundException("Organization not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


def org_admin_update_organization_service(
    org_id: UUID,
    data: OrganizationOrgAdminUpdateSchema,
) -> OrganizationOutSchema:
    """
    Restricted update — org admin can only change name and industry.
    Cannot change slug, is_active, or anything structural.
    """
    try:
        org =  Organizations.objects.get(id=org_id)
        update_data = data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(org, field, value)
        org.save()
        return OrganizationOutSchema(org)
    except Organizations.DoesNotExist:
        raise NotFoundException("Organization not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


def deactivate_organization_service(
    org_id: UUID,
) -> None:
    """
    Soft deletes an organization by marking it inactive.
    Superuser only.
    """
    try:
        org = Organizations.objects.get(id=org_id)
        org.is_active = False
        org.save()
    except Organizations.DoesNotExist:
        raise NotFoundException("Organization not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


def get_org_settings_service(
    org_id: UUID,
) -> OrganizationSettingsOutSchema:
    """Retrieves settings for an organization."""
    try:
        settings = OrganizationSettings.objects.get(
            organization_id=org_id
        )
        return OrganizationSettingsOutSchema(settings)
    except OrganizationSettings.DoesNotExist:
        raise NotFoundException("Organization settings not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


def update_org_settings_service(
    org_id: UUID,
    data: OrganizationSettingsUpdateSchema,
) -> OrganizationSettingsOutSchema:
    """
    Updates organization settings.
    Org admin and superuser can update these.
    """
    try:
        settings, _ = OrganizationSettings.objects.get_or_create(
            organization_id=org_id
        )
        update_data = data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(settings, field, value)
        settings.save()
        return OrganizationSettingsOutSchema(settings)
    except Exception as e:
        raise BadRequestException(str(e)) from e


# ##### Helpers #########################

# def _org_to_schema(org: Organizations) -> OrganizationOutSchema:
#     return OrganizationOutSchema(org)


# def _settings_to_schema(
#     settings: OrganizationSettings,
# ) -> OrganizationSettingsOutSchema:
#     return OrganizationSettingsOutSchema(settings)
