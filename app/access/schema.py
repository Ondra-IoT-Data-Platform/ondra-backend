from ninja import ModelSchema, Schema

from app.access.models import VerificationTokens


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
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenSchema(Schema):
    refresh_token: str


class VerifyEmailSchema(Schema):
    email: str
    token: str


class VerificationTokenResponseSchema(Schema):
    email: str
    token: str
    message: str
