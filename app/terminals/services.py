from uuid import UUID

from django.db import transaction
from organization.models import Organizations
from config.exceptions import BadRequestException, NotFoundException
from terminals.models import Gates, Terminals
from terminals.schema import (
    GateCreateSchema,
    GateOutSchema,
    GateUpdateSchema,
    TerminalCreateSchema,
    TerminalOutSchema,
    TerminalUpdateSchema,
    TerminalWithGatesOutSchema,
)



######## Terminals ####################################

def create_terminal_service(
    org_id: UUID,
    data: TerminalCreateSchema,
) -> TerminalOutSchema:
    """Creates a new terminal"""
    try:
        org = Organizations.objects.filter(id=org_id, is_active=True).first()

        if not org:
            raise NotFoundException("Organization not found") from None

        if not org.is_active:
            raise BadRequestException("Organization is not active") from None
        with transaction.atomic():
            terminal = Terminals.objects.create(organization_id=org_id, **data.dict())
        return TerminalOutSchema.from_orm(terminal)
    except Exception as e:
        raise BadRequestException(str(e)) from e


def list_terminals_service(
    org_id: UUID,
) -> list[TerminalOutSchema]:
    """Lists all terminals for an organization"""
    try:
        # TODO: validate request.user belongs to this organization
        terminals = Terminals.objects.filter(organization_id=org_id)
        return [TerminalOutSchema.from_orm(t) for t in terminals]
    except Exception as e:
        raise BadRequestException(str(e)) from e


def get_terminal_service(
    authenticated_user,
    org_id: UUID,
    terminal_id: int,
) -> TerminalOutSchema:
    """Retrieves a single terminal by id"""
    try:
        terminal = Terminals.objects.get(id=terminal_id)
        return TerminalOutSchema.from_orm(terminal)
    except Terminals.DoesNotExist:
        raise NotFoundException("Terminal not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


def get_terminal_with_gates_service(
    org_id: UUID,
    terminal_id: int,
) -> TerminalWithGatesOutSchema:
    """Retrieves a terminal along with its related gates"""
    try:
        terminal = Terminals.objects.get(id=terminal_id)
        gates = [gate for gate in terminal.gates.all()]
        return TerminalWithGatesOutSchema(
            id=terminal.id,
            name=terminal.name,
            location=terminal.location,
            longitude=terminal.longitude,
            latitude=terminal.latitude,
            organization=terminal.organization_id,
            status=terminal.status,
            created_at=terminal.created_at,
            updated_at=terminal.updated_at,
            gates=gates,
        )
    except Terminals.DoesNotExist:
        raise NotFoundException("Terminal not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


def update_terminal_service(
    org_id: UUID,
    terminal_id: int,
    data: TerminalUpdateSchema,
) -> TerminalOutSchema:
    """Updates an existing terminal"""
    try:
        # TODO: validate request.user has permission to update this terminal
        terminal = Terminals.objects.get(id=terminal_id)
        update_data = data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(terminal, field, value)
        terminal.save()
        return TerminalOutSchema.from_orm(terminal)
    except Terminals.DoesNotExist:
        raise NotFoundException("Terminal not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


def delete_terminal_service(
    org_id: UUID,
    terminal_id: int,
) -> None:
    """Deletes a terminal"""
    try:
        # TODO: validate request.user has permission to delete this terminal
        terminal = Terminals.objects.get(id=terminal_id)
        terminal.delete()
    except Terminals.DoesNotExist:
        raise NotFoundException("Terminal not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


# ── Gates ──────────────────────────────────────────────────

def create_gate_service(
    org_id: UUID,
    data: GateCreateSchema,
) -> GateOutSchema:
    """Creates a new gate under a terminal"""
    try:
        # TODO: validate request.user has permission to create gates
        # for this terminal's organization
        terminal_exists = Terminals.objects.filter(
            id=data.terminal_id,
            organization_id=org_id
        ).aexists()
        if not terminal_exists:
            raise NotFoundException("Terminal not found") from None

        gate = Gates.objects.create(**data.dict())
        return GateOutSchema.from_orm(gate)
    except NotFoundException:
        raise
    except Exception as e:
        raise BadRequestException(str(e)) from e


def list_gates_service(
    org_id: UUID,
    terminal_id: int,
) -> list[GateOutSchema]:
    """Lists all gates for a given terminal"""
    try:
        # TODO: validate request.user belongs to the organization
        # that owns this terminal
        gates = Gates.objects.filter(terminal_id=terminal_id)
        return [GateOutSchema.from_orm(g) for g in gates]
    except Exception as e:
        raise BadRequestException(str(e)) from e


def get_gate_service(
    org_id: UUID,
    gate_id: int,
) -> GateOutSchema:
    """Retrieves a single gate by id"""
    try:
        gate = Gates.objects.get(id=gate_id)
        return GateOutSchema.from_orm(gate)
    except Gates.DoesNotExist:
        raise NotFoundException("Gate not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


def update_gate_service(
    org_id: UUID,
    gate_id: int,
    data: GateUpdateSchema,
) -> GateOutSchema:
    """Updates an existing gate"""
    try:
        # TODO: validate request.user has permission to update this gate
        gate = Gates.objects.get(id=gate_id)
        update_data = data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(gate, field, value)
        gate.save()
        return GateOutSchema.from_orm(gate)
    except Gates.DoesNotExist:
        raise NotFoundException("Gate not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


def delete_gate_service(
    org_id: UUID,
    gate_id: int,
) -> None:
    """Deletes a gate"""
    try:
        # TODO: validate request.user has permission to delete this gate
        gate = Gates.objects.get(id=gate_id)
        gate.delete()
    except Gates.DoesNotExist:
        raise NotFoundException("Gate not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e
