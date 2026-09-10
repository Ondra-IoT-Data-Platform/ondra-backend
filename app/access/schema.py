from typing import Optional, Dict, Any, List
from datetime import datetime
from typing import Optional
from uuid import UUID
from enum import Enum

from ninja import ModelSchema, Schema, Field
from users.schema import UserOutSchema



# ============ AUTH SCHEMAS ============
class LoginSchema(Schema):
    email: str
    password: str


class LoginResponseSchema(Schema):
    access_token: str
    refresh_token: str
    expires_in: int
    user: UserOutSchema


class RefreshTokenSchema(Schema):
    refresh_token: str


class RefreshTokenResponseSchema(Schema):
    access_token: str
    expires_in: int


class OTPRequestSchema(Schema):
    purpose: str


class OTPVerifySchema(Schema):
    phone_number: str
    token: str
    purpose: str


class OTPResponseSchema(Schema):
    expires_in: int


class LogoutSchema(Schema):
    refresh_token: str



# ============ TOKEN SCHEMAS ============
class TokenTypeEnum(str, Enum):
    """Token type enum for API validation."""
    USER_ONBOARDING = "user_onboarding"
    EMAIL_VERIFICATION = "email_verification"
    INVITATION = "invitation"
    PASSWORD_RESET = "password_reset"
    TWO_FACTOR_AUTH = "two_factor_auth"
    REFRESH_TOKEN = "refresh_token"
    DELIVERY_CONFIRMATION = "delivery_confirmation"


# ============ REQUEST SCHEMAS ============
class TokenCreateSchema(Schema):
    """Schema for creating a new token."""
    organization_id: UUID
    email: Optional[str] = None
    user_id: Optional[UUID] = None
    token_type: TokenTypeEnum = TokenTypeEnum.USER_ONBOARDING
    expires_in_hours: int = Field(24, ge=1, le=720)  # 1 hour to 30 days
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

    # Additional fields for specific token types
    role: Optional[str] = Field(None, description="Role for invitation tokens")
    redirect_url: Optional[str] = Field(None, description="Redirect URL for verification tokens")

class TokenValidationSchema(Schema):
    """Schema for validating a token."""
    token: str = Field(..., min_length=32, description="The raw token string")
    organization_id: Optional[UUID] = None
    token_type: Optional[TokenTypeEnum] = None


class TokenRevokeSchema(Schema):
    """Schema for revoking a token."""
    token: str = Field(..., min_length=32)
    organization_id: Optional[UUID] = None
    reason: Optional[str] = Field(None, max_length=255)


class TokenExtendSchema(Schema):
    """Schema for extending token expiry."""
    token: str = Field(..., min_length=32)
    organization_id: Optional[UUID] = None
    additional_hours: int = Field(24, ge=1, le=720)

class TokenBulkCreateSchema(Schema):
    """Schema for bulk token creation."""
    organization_id: UUID
    emails: List[str] = Field(..., max_items=100)
    token_type: TokenTypeEnum = TokenTypeEnum.INVITATION
    expires_in_hours: int = Field(72, ge=1, le=720)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class TokenFilterSchema(Schema):
    """Schema for filtering tokens."""
    token_type: Optional[TokenTypeEnum] = None
    organization_id: Optional[UUID] = None
    user_id: Optional[UUID] = None
    email: Optional[str] = None
    is_used: Optional[bool] = None
    is_revoked: Optional[bool] = None
    is_expired: Optional[bool] = None
    created_after: Optional[datetime] = None
    created_before: Optional[datetime] = None
    expires_after: Optional[datetime] = None
    expires_before: Optional[datetime] = None
    limit: int = Field(100, ge=1, le=500)
    offset: int = Field(0, ge=0)


# ============ TOKEN RESPONSE SCHEMAS ============
class TokenResponseSchema(Schema):
    """Base schema for token response."""
    id: UUID
    token: str  # Raw token - only returned when created
    token_hash: Optional[str] = None  # Hash - only for internal use
    token_type: str
    email: Optional[str]
    user_id: Optional[UUID]
    organization_id: UUID
    is_used: bool
    is_revoked: bool
    metadata: Optional[Dict[str, Any]]
    expires_at: datetime
    created_at: datetime

    # Computed properties
    is_valid: bool

    class Config:
        from_attribute = True


class TokenDetailResponseSchema(Schema):
    """Detailed token response with additional info."""
    id: UUID
    token_type: str
    email: Optional[str]
    user_id: Optional[UUID]
    organization_id: UUID
    organization_name: str
    is_used: bool
    is_revoked: bool
    is_expired: bool
    metadata: Optional[Dict[str, Any]]
    expires_at: datetime
    created_at: datetime

    # Token usage info
    used_at: Optional[datetime] = None
    revoked_at: Optional[datetime] = None
    revoked_reason: Optional[str] = None

    class Config:
        from_attribute = True


class TokenValidationResponseSchema(Schema):
    """Schema for token validation response."""
    valid: bool
    token_id: Optional[UUID] = None
    token_type: Optional[str] = None
    organization_id: Optional[UUID] = None
    organization_name: Optional[str] = None
    email: Optional[str] = None
    user_id: Optional[UUID] = None
    expires_at: Optional[datetime] = None
    is_used: bool = False
    is_revoked: bool = False
    error: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None


class TokenStatisticsSchema(Schema):
    """Schema for token statistics."""
    total: int
    active: int  # Not used, not revoked, not expired
    used: int
    revoked: int
    expired: int
    by_type: Dict[str, int]  # Count by token type
    by_organization: Optional[Dict[str, int]] = None  # Count by organization


class TokenBulkCreateResponseSchema(Schema):
    """Schema for bulk token creation response."""
    total_created: int
    tokens: List[TokenResponseSchema]
    errors: Optional[List[Dict[str, str]]] = None


class UserTokenResponseSchema(Schema):
    """Schema for user's token list response."""
    id: UUID
    token_type: str
    organization_id: UUID
    organization_name: str
    is_used: bool
    is_valid: bool
    expires_at: datetime
    created_at: datetime

    class Config:
        from_attribute = True


# ============ ONBOARDING SPECIFIC SCHEMAS ============
class OnboardingTokenGenerateSchema(Schema):
    """Schema for generating an onboarding token."""
    organization_id: UUID
    email: str = Field(..., max_length=255)
    first_name: Optional[str] = Field(None, max_length=150)
    last_name: Optional[str] = Field(None, max_length=150)
    phone: Optional[str] = Field(None, max_length=20)
    role: Optional[str] = Field("org_admin", description="Role in organization")
    expires_in_hours: Optional[int] = Field(24, ge=1, le=720)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class OnboardingCompleteSchema(Schema):
    """Schema for completing onboarding."""
    token: str = Field(..., min_length=32)
    organization_id: Optional[UUID] = None


class OnboardingTokenResponseSchema(Schema):
    """Schema for onboarding token response."""
    token_id: UUID
    token: str  # Raw token for the user
    organization_id: UUID
    organization_name: str
    email: str
    user_id: Optional[UUID] = None
    expires_at: datetime
    is_used: bool = False

    class Config:
        from_attribute = True





class InvitationTokenResponseSchema(Schema):
    """Schema for invitation token response."""
    token: str  # Raw token to return to browser
    token_id: UUID
    email: str
    organization_id: UUID
    organization_name: str
    role: str
    expires_at: datetime
    is_used: bool
    is_revoked: bool
    is_valid: bool
    created_at: datetime
    message: Optional[str] = None

    class Config:
        from_attribute = True


class TokenStatusResponseSchema(Schema):
    """Schema for token status response."""
    valid: bool
    token_id: Optional[UUID] = None
    email: Optional[str] = None
    organization_id: Optional[UUID] = None
    organization_name: Optional[str] = None
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    role: Optional[str] = None
    token_type: Optional[str] = None
    expires_at: Optional[datetime] = None
    is_used: Optional[bool] = None
    is_revoked: Optional[bool] = None
    is_expired: Optional[bool] = None
    metadata: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class TokenListResponseSchema(Schema):
    """Schema for token list response."""
    id: UUID
    token_type: str
    email: str
    organization_id: UUID
    organization_name: str
    is_used: bool
    is_revoked: bool
    is_valid: bool
    expires_at: datetime
    created_at: datetime
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attribute = True

# ============ INVITATION SPECIFIC SCHEMAS ============
class InvitationTokenGenerateSchema(Schema):
    """Schema for generating an invitation token."""
    organization_id: UUID
    email: str = Field(..., max_length=255)
    role: Optional[str] = Field("org_admin")
    expires_in_hours: Optional[int] = Field(72, ge=1, le=720)
    invited_by_id: Optional[UUID] = None
    message: Optional[str] = Field(None, max_length=500)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)


class InvitationAcceptSchema(Schema):
    """Schema for accepting invitation."""
    token: str = Field(..., min_length=32)
    first_name: str
    last_name: str
    phone: Optional[str] = None
    password: str
    organization_id: Optional[UUID] = None


class InvitationResponseSchema(Schema):
    """Schema for invitation response."""
    token: str
    email: str
    organization_id: UUID
    organization_name: str
    role: str
    expires_at: datetime
    created_at: datetime

    class Config:
        from_attribute = True


# ============ PAGINATION SCHEMAS ============
class PaginatedTokenResponseSchema(Schema):
    """Schema for paginated token list."""
    items: List[TokenResponseSchema]
    total: int
    limit: int
    offset: int
    has_more: bool


# ============ ADMIN SCHEMAS ============
class AdminTokenUpdateSchema(Schema):
    """Schema for admin token updates."""
    is_revoked: Optional[bool] = None
    is_used: Optional[bool] = None
    expires_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None
    revoke_reason: Optional[str] = None


class TokenCleanupResponseSchema(Schema):
    """Schema for token cleanup response."""
    deleted_count: int
    token_types_deleted: Dict[str, int]  # Count by token type
    total_remaining: int


# ============ CUSTOM FIELD VALIDATORS ============
class PasswordResetTokenCreateSchema(Schema):
    """Schema for creating password reset token."""
    email: str
    expires_in_hours: int = Field(24, ge=1, le=72)


class EmailVerificationTokenCreateSchema(Schema):
    """Schema for creating email verification token."""
    user_id: UUID
    expires_in_hours: int = Field(24, ge=1, le=72)
    redirect_url: Optional[str] = None


class TwoFactorAuthTokenCreateSchema(Schema):
    """Schema for creating 2FA token."""
    user_id: UUID
    expires_in_minutes: int = Field(10, ge=1, le=30)
    method: str = "totp"  # or "sms", "email"


# ============ MAPPING FUNCTIONS ============
def map_token_to_response(token) -> TokenResponseSchema:
    """Map token model to response schema."""
    return TokenResponseSchema(
        id=token.id,
        token=token.token,  # Only if it's a raw token
        token_hash=token.token_hash,
        token_type=token.token_type,
        email=token.email,
        user_id=token.user_id if token.user else None,
        organization_id=token.organization_id,
        is_used=token.is_used,
        is_revoked=token.is_revoked,
        metadata=token.metadata,
        expires_at=token.expires_at,
        created_at=token.created_at,
        is_valid=token.is_valid
    )


def map_token_to_detail_response(token, organization_name: str = None) -> TokenDetailResponseSchema:
    """Map token model to detailed response schema."""
    return TokenDetailResponseSchema(
        id=token.id,
        token_type=token.token_type,
        email=token.email,
        user_id=token.user_id if token.user else None,
        organization_id=token.organization_id,
        organization_name=organization_name or token.organization.name,
        is_used=token.is_used,
        is_revoked=token.is_revoked,
        is_expired=token.is_expired,
        metadata=token.metadata,
        expires_at=token.expires_at,
        created_at=token.created_at,
        used_at=token.metadata.get('used_at') if token.metadata else None,
        revoked_at=token.metadata.get('revoked_at') if token.metadata else None,
        revoked_reason=token.metadata.get('revoked_reason') if token.metadata else None
    )


def map_token_validation_response(
    token,
    error: Optional[str] = None
) -> TokenValidationResponseSchema:
    """Map token validation result to response schema."""
    if error:
        return TokenValidationResponseSchema(
            valid=False,
            error=error
        )

    return TokenValidationResponseSchema(
        valid=True,
        token_id=token.id,
        token_type=token.token_type,
        organization_id=token.organization_id,
        organization_name=token.organization.name,
        email=token.email,
        user_id=token.user_id if token.user else None,
        expires_at=token.expires_at,
        is_used=token.is_used,
        is_revoked=token.is_revoked,
        metadata=token.metadata
    )

def map_token_to_onboarding_response(
    raw_token: str,
    token_obj,
    organization
) -> OnboardingTokenResponseSchema:
    """Map token model to onboarding response schema."""
    metadata = token_obj.metadata or {}

    return OnboardingTokenResponseSchema(
        token=raw_token,
        token_id=token_obj.id,
        email=token_obj.email,
        organization_id=token_obj.organization_id or organization.id,
        organization_name=organization.name,
        role=metadata.get('role', 'org_admin'),
        expires_at=token_obj.expires_at,
        is_used=token_obj.is_used,
        is_revoked=token_obj.is_revoked,
        is_valid=token_obj.is_valid,
        created_at=token_obj.created_at
    )


def map_token_to_invitation_response(
    raw_token: str,
    token_obj,
    organization
) -> InvitationTokenResponseSchema:
    """Map token model to invitation response schema."""
    metadata = token_obj.metadata or {}

    return InvitationTokenResponseSchema(
        token=raw_token,
        token_id=token_obj.id,
        email=token_obj.email,
        organization_id=token_obj.organization_id or organization.id,
        organization_name=organization.name,
        role=metadata.get('role', 'org_admin'),
        expires_at=token_obj.expires_at,
        is_used=token_obj.is_used,
        is_revoked=token_obj.is_revoked,
        is_valid=token_obj.is_valid,
        created_at=token_obj.created_at,
        message=metadata.get('message')
    )


def map_token_to_status_response(
    token_obj,
    valid: bool,
    error: Optional[str] = None
) -> TokenStatusResponseSchema:
    """Map token model to status response schema."""
    if not valid or not token_obj:
        return TokenStatusResponseSchema(
            valid=False,
            error=error or "Token is invalid"
        )

    metadata = token_obj.metadata or {}

    return TokenStatusResponseSchema(
        valid=True,
        token_id=token_obj.id,
        email=token_obj.email,
        organization_id=token_obj.organization_id,
        organization_name=token_obj.organization.name if token_obj.organization else None,
        first_name=metadata.get('first_name'),
        last_name=metadata.get('last_name'),
        phone=metadata.get('phone'),
        role=metadata.get('role', 'org_admin'),
        token_type=token_obj.token_type,
        expires_at=token_obj.expires_at,
        is_used=token_obj.is_used,
        is_revoked=token_obj.is_revoked,
        is_expired=token_obj.is_expired,
        metadata=token_obj.metadata
    )


def map_token_list_response(token_obj) -> TokenListResponseSchema:
    """Map token model to list response schema."""
    return TokenListResponseSchema(
        id=token_obj.id,
        token_type=token_obj.token_type,
        email=token_obj.email,
        organization_id=token_obj.organization_id,
        organization_name=token_obj.organization.name if token_obj.organization else None,
        is_used=token_obj.is_used,
        is_revoked=token_obj.is_revoked,
        is_valid=token_obj.is_valid,
        expires_at=token_obj.expires_at,
        created_at=token_obj.created_at,
        metadata=token_obj.metadata
    )
