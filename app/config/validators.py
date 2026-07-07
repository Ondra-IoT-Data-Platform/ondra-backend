from config.exceptions import ForbiddenException
from typing import  Any



class TenantService:
    def __init__(self, request):
        self.user = request.auth
        self.org_id = request.auth.get("org_id")

        if not self.org_id:
            raise ForbiddenException(
                "User does not belong to an organization"
            ) from None

    def check_tenant(self,  object: dict | Any) -> dict | None:
        """
        Checks if request.auth belongs to organization
        if organization object is present
        """
        object_org_id = str(getattr(object, "organization", getattr(object, "org_id", None)))
        if self.org_id != object_org_id:
            return None
        return object

    def check_tenant_id(self, org_id: str) -> str | None:
        """
        Checks if request.auth belongs to organization
        if organization ID is present
        """
        if self.org_id != str(org_id):
            return None
        return org_id
