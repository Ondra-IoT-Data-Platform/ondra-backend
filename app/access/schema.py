from ninja import ModelSchema, Schema
from ninja_jwt.schema import TokenObtainPairInputSchema
from ninja_jwt.tokens import RefreshToken
from access.models import VerificationTokens

from typing import Optional



class CustomTokenObtainPairInputSchema(TokenObtainPairInputSchema):
    """
    Extends ninja-jwt's default login schema.
    Adds org_id, role_id, and role_name to the token claims.
    """

    @classmethod
    def get_token(cls, user) -> RefreshToken:
        token = super().get_token(user)

        # Add custom claims
        token["org_id"] = str(user.organization_id)
        token["role_id"] = str(user.role_id)
        token["role_name"] = user.role.name if user.role else None
        token["is_superuser"] = user.is_superuser

        return token

class CustomTokenObtainPairOutputSchema(Schema):
    """
    What the login endpoint returns to the client.
    Extends the default with role and organization info.
    """
    access: str
    refresh: str
    token_type: str = "bearer"
    role: Optional[str] = None
    organization: Optional[str] = None


class VerificationTokenSchema(ModelSchema):
    class Meta:
        model = VerificationTokens
        fields = "__all__"


class VerificationTokenCreateSchema(ModelSchema):
    class Meta:
        model = VerificationTokens
        fields = ["token_type"]


class VerificationTokenUpdateSchema(ModelSchema):
    class Meta:
        model = VerificationTokens
        fields = ["is_used"]


class LoginSchema(Schema):
    email: str
    password: str


class LoginResponseSchema(Schema):
    access: str
    refresh: str
    token_type: str = "bearer"
    role: Optional[str] = None
    organization: Optional[str] = None


class RefreshTokenSchema(Schema):
    refresh_token: str


class VerifyEmailSchema(Schema):
    email: str
    token: str


class VerificationTokenResponseSchema(Schema):
    email: str
    token: str
    message: str
