
##################################################
# ----------- ADMIN PRIVILEGE FOR NOW -------
##################################################


from uuid import UUID
from django.contrib.auth import get_user_model
from asgiref.sync import sync_to_async
from config.exceptions import (
    BadRequestException,
    NotFoundException,
    ForbiddenException,
)

from organization.schema import (
    OrganizationCreateSchema,
    OrganizationUpdateSchema,
    OrganizationOrgAdminUpdateSchema,
    OrganizationOutSchema,
    OrganizationSettingsUpdateSchema,
    OrganizationSettingsOutSchema
)
from organization.models import Organizations, OrganizationSettings


User = get_user_model()



async def create_organization_service(
    data: OrganizationCreateSchema,
) -> OrganizationOutSchema:
    """
    Creates a new organization.
    Superuser only.
    Seeds all 8 roles automatically after creation.
    """
    try:
        exists = await Organizations.objects.filter(
            slug=data.slug
        ).aexists()
        if exists:
            from config.exceptions import ConflictException
            raise ConflictException(
                f"Organization with slug '{data.slug}' already exists"
            ) from None

        org = await Organizations.objects.acreate(**data.dict())

        # Seed roles for the new organization
        await _seed_org_roles(org)

        return OrganizationOutSchema(org)
    except Exception as e:
        if "already exists" in str(e).lower() or "conflict" in type(e).__name__.lower():
            raise
        raise BadRequestException(str(e)) from e


async def _seed_org_roles(org: Organizations) -> None:
    """Seeds all 8 default roles for a new organization."""
    from users.models import Role

    for role_name, _ in Role.RoleName.choices:
        await Role.objects.aget_or_create(
            name=role_name,
            organization=org,
        )


async def list_organizations_service() -> list[OrganizationOutSchema]:
    """
    Lists all organizations.
    Superuser only.
    """
    try:
        orgs = Organizations.objects.filter(is_active=True).order_by("name")
        return [OrganizationOutSchema(org) async for org in orgs]
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def get_organization_service(
    org_id: UUID,
) -> OrganizationOutSchema:
    """
    Retrieves a single organization.
    Superuser can get any org.
    Org admin can only get their own org.
    """
    try:
        org = await Organizations.objects.aget(id=org_id)
        return OrganizationOutSchema(org)
    except Organizations.DoesNotExist:
        raise NotFoundException("Organization not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def update_organization_service(
    org_id: UUID,
    data: OrganizationUpdateSchema,
) -> OrganizationOutSchema:
    """
    Full update — superuser only.
    Can update any field including is_active and slug.
    """
    try:
        org = await Organizations.objects.aget(id=org_id)
        update_data = data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(org, field, value)
        await org.asave()
        return OrganizationOutSchema(org)
    except Organizations.DoesNotExist:
        raise NotFoundException("Organization not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def org_admin_update_organization_service(
    org_id: UUID,
    data: OrganizationOrgAdminUpdateSchema,
) -> OrganizationOutSchema:
    """
    Restricted update — org admin can only change name and industry.
    Cannot change slug, is_active, or anything structural.
    """
    try:
        org = await Organizations.objects.aget(id=org_id)
        update_data = data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(org, field, value)
        await org.asave()
        return OrganizationOutSchema(org)
    except Organizations.DoesNotExist:
        raise NotFoundException("Organization not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def deactivate_organization_service(
    org_id: UUID,
) -> None:
    """
    Soft deletes an organization by marking it inactive.
    Superuser only.
    """
    try:
        org = await Organizations.objects.aget(id=org_id)
        org.is_active = False
        await org.asave()
    except Organizations.DoesNotExist:
        raise NotFoundException("Organization not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def get_org_settings_service(
    org_id: UUID,
) -> OrganizationSettingsOutSchema:
    """Retrieves settings for an organization."""
    try:
        settings = await OrganizationSettings.objects.aget(
            organization_id=org_id
        )
        return OrganizationSettingsOutSchema(settings)
    except OrganizationSettings.DoesNotExist:
        raise NotFoundException("Organization settings not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def update_org_settings_service(
    org_id: UUID,
    data: OrganizationSettingsUpdateSchema,
) -> OrganizationSettingsOutSchema:
    """
    Updates organization settings.
    Org admin and superuser can update these.
    """
    try:
        settings, _ = await OrganizationSettings.objects.aget_or_create(
            organization_id=org_id
        )
        update_data = data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(settings, field, value)
        await settings.asave()
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
