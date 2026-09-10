# access/token_services.py
from datetime import timedelta
import email
from typing import Optional, Tuple, Dict, Any
from uuid import UUID

from django.utils import timezone

from config.exceptions import BadRequestException, NotFoundException
from access.auth_utils import OTokenManager
from access.models import TokenTypeChoices, OrganizationTokens
from access.schema import (
    OnboardingTokenGenerateSchema,
    OnboardingTokenResponseSchema,
    TokenStatusResponseSchema,
    InvitationTokenGenerateSchema,
    InvitationTokenResponseSchema,
    TokenValidationSchema,
    TokenRevokeSchema,
    TokenExtendSchema,
    map_token_to_onboarding_response,
    map_token_to_invitation_response,
    map_token_to_status_response
)
from organization.models import Organizations


class TokenService:
    """
    Service for generating organization onboarding tokens.
    Only handles token generation - user creation is handled separately.
    """

    @staticmethod
    def generate_organization_onboarding_token(
        payload: OnboardingTokenGenerateSchema
    ) -> OnboardingTokenResponseSchema:
        """
        Generate an onboarding token signed with the organization.
        Token is returned to the browser for user creation flow.

        Args:
            payload: OnboardingTokenGenerateSchema instance containing token generation parameters

        Returns:
            OnboardingTokenResponseSchema: The generated onboarding token response

        Raises:
            NotFoundException: If organization doesn't exist
            BadRequestException: If token already exists or validation fails
        """
        # Validate organization exists
        try:
            organization = Organizations.objects.get(id=payload.organization_id, is_active=True)
        except Organizations.DoesNotExist:
            raise NotFoundException("Organization not found")

        # Check if there's already a valid onboarding token for this email
        existing_token = OrganizationTokens.objects.filter(
            organization_id=payload.organization_id,
            email=payload.email,
            token_type=TokenTypeChoices.USER_ONBOARDING,
            is_used=False,
            is_revoked=False,
            expires_at__gt=timezone.now()
        ).first()

        if existing_token:
            raise BadRequestException(
                "A valid onboarding token already exists for this email and organization"
            )


        metadata = {}
        metadata['role'] = payload.role
        # Generate token using OTokenManager
        raw_token, token_obj = OTokenManager.generate_onboarding_token(
            email=payload.email,
            organization_id=str(payload.organization_id),
            expires_in_hours=payload.expires_in_hours,
            metadata=metadata,
        )

        return map_token_to_onboarding_response(raw_token, token_obj, organization)

    @staticmethod
    def generate_organization_invitation_token(
        payload: InvitationTokenGenerateSchema
    ) -> InvitationTokenResponseSchema:
        """
        Generate an invitation token for a user to join an organization.

        Args:
            payload: InvitationTokenGenerateSchema instance containing token generation parameters

        Returns:
            InvitationTokenResponseSchema: The generated invitation token response

        Raises:
            NotFoundException: If organization doesn't exist
            BadRequestException: If user already exists or validation fails
        """
        # Validate organization exists
        try:
            organization = Organizations.objects.get(id=payload.organization_id, is_active=True)
        except Organizations.DoesNotExist:
            raise NotFoundException("Organization not found")

        # Check for existing valid invitation
        existing_token = OrganizationTokens.objects.filter(
            organization_id=payload.organization_id,
            email=payload.email,
            token_type=TokenTypeChoices.INVITATION,
            is_used=False,
            is_revoked=False,
            expires_at__gt=timezone.now()
        ).first()

        if existing_token:
            raise BadRequestException("A valid invitation already exists for this email")

        # Generate invitation token
        raw_token, token_obj = OTokenManager.generate_invitation_token(
            organization_id=str(payload.organization_id),
            email=payload.email,
            role=payload.role,
            expires_in_hours=payload.expires_in_hours,
            invited_by_id=str(payload.invited_by_id) if payload.invited_by_id else None
        )

        # Add custom message to metadata
        if payload.message:
            token_obj.metadata['message'] = payload.message
            token_obj.save(update_fields=['metadata'])

        return raw_token, token_obj

    @staticmethod
    def validate_onboarding_token(
        payload: TokenValidationSchema
    ) -> OrganizationTokens:
        """
        Validate an onboarding token.

        Args:
            raw_token: The raw token string
            organization_id: Optional organization ID for validation

        Returns:
            OrganizationTokens: Valid token object

        Raises:
            BadRequestException: If token is invalid, expired, or doesn't match organization
        """
        token_obj = OTokenManager.verify_otoken(
            payload.token,
            payload.token_type
        )

        if not token_obj:
            raise BadRequestException("Invalid or expired onboarding token")

        # Check organization if provided
        if payload.organization_id and str(token_obj.organization_id) != str(payload.organization_id):
            raise BadRequestException("Token doesn't belong to the specified organization")

        return token_obj

    @staticmethod
    def validate_invitation_token(
        raw_token: str,
        organization_id: Optional[UUID] = None
    ) -> OrganizationTokens:
        """
        Validate an invitation token.

        Args:
            raw_token: The raw token string
            organization_id: Optional organization ID for validation

        Returns:
            OrganizationTokens: Valid token object

        Raises:
            BadRequestException: If token is invalid, expired, or doesn't match organization
        """
        token_obj = OTokenManager.verify_otoken(
            raw_token,
            TokenTypeChoices.INVITATION
        )

        if not token_obj:
            raise BadRequestException("Invalid or expired invitation token")

        # Check organization if provided
        if organization_id and str(token_obj.organization_id) != str(organization_id):
            raise BadRequestException("Token doesn't belong to the specified organization")

        return token_obj

    @staticmethod
    def get_token_status(
        raw_token: str,
        organization_id: Optional[UUID] = None
    ) -> Dict[str, Any]:
        """
        Get the status of a token without consuming it.

        Args:
            raw_token: The raw token string
            organization_id: Optional organization ID for validation

        Returns:
            Dict[str, Any]: Token status information
        """
        try:
            token_obj = TokenService.validate_onboarding_token(raw_token, organization_id)

            return {
                'valid': True,
                'token_id': str(token_obj.id),
                'email': token_obj.email,
                'organization_id': str(token_obj.organization.id) if token_obj.organization else None,
                'organization_name': token_obj.organization.name if token_obj.organization else None,
                'token_type': token_obj.token_type,
                'expires_at': token_obj.expires_at,
                'is_used': token_obj.is_used,
                'is_revoked': token_obj.is_revoked,
                'is_expired': token_obj.is_expired,
                'metadata': token_obj.metadata
            }
        except BadRequestException as e:
            return {
                'valid': False,
                'error': str(e)
            }

    @staticmethod
    def revoke_token(
        raw_token: str,
        reason: Optional[str] = "Revoked by admin"
    ) -> None:
        """
        Revoke a token.

        Args:
            raw_token: The raw token string
            reason: Reason for revocation

        Raises:
            BadRequestException: If token is invalid
        """
        token_obj = TokenService.validate_onboarding_token(raw_token)
        OTokenManager.mark_revoked(token_obj, reason)

    @staticmethod
    def extend_token_expiry(
        raw_token: str,
        additional_hours: int = 24,
        organization_id: Optional[UUID] = None
    ) -> OrganizationTokens:
        """
        Extend the expiry of a token.

        Args:
            raw_token: The raw token string
            additional_hours: Hours to add to expiry
            organization_id: Optional organization ID for validation

        Returns:
            OrganizationTokens: Updated token object

        Raises:
            BadRequestException: If token is invalid
        """
        token_obj = TokenService.validate_onboarding_token(raw_token, organization_id)

        # Extend expiry
        token_obj.expires_at = timezone.now() + timedelta(hours=additional_hours)
        token_obj.save(update_fields=['expires_at'])

        return token_obj

    @staticmethod
    def mark_token_as_used(token_obj: OrganizationTokens) -> None:
        """
        Mark a token as used.
        Called by user service after user creation.

        Args:
            token_obj: Token instance

        Raises:
            BadRequestException: If token is already used
        """
        if token_obj.is_used:
            raise BadRequestException("Token is already used")

        OTokenManager.mark_used(token_obj)

    @staticmethod
    def get_tokens_for_organization(
        organization_id: UUID,
        token_type: Optional[str] = None,
        include_used: bool = False
    ) -> list:
        """
        Get all tokens for an organization.

        Args:
            organization_id: Organization UUID
            token_type: Optional token type filter
            include_used: Whether to include used tokens

        Returns:
            list: List of token objects

        Raises:
            NotFoundException: If organization doesn't exist
        """
        # Validate organization exists
        try:
            Organizations.objects.get(id=organization_id, is_active=True)
        except Organizations.DoesNotExist:
            raise NotFoundException("Organization not found")

        query = OrganizationTokens.objects.filter(
            organization_id=organization_id,
            is_revoked=False
        ).select_related('user')

        if not include_used:
            query = query.filter(is_used=False)

        if token_type:
            query = query.filter(token_type=token_type)

        return query.order_by('-created_at')
