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

async def create_terminal_service(
    user,
    data: TerminalCreateSchema,
) -> TerminalOutSchema:
    """Creates a new terminal"""
    try:
        terminal = await Terminals.objects.acreate(**data.dict())
        return TerminalOutSchema.from_orm(terminal)
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def list_terminals_service(
    organization_id: int,
) -> list[TerminalOutSchema]:
    """Lists all terminals for an organization"""
    try:
        # TODO: validate request.user belongs to this organization
        terminals = Terminals.objects.filter(organization_id=organization_id)
        return [TerminalOutSchema.from_orm(t) async for t in terminals]
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def get_terminal_service(
    authenticated_user,
    terminal_id: int,
) -> TerminalOutSchema:
    """Retrieves a single terminal by id"""
    try:
        terminal = await Terminals.objects.aget(id=terminal_id)
        return TerminalOutSchema.from_orm(terminal)
    except Terminals.DoesNotExist:
        raise NotFoundException("Terminal not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def get_terminal_with_gates_service(
    terminal_id: int,
) -> TerminalWithGatesOutSchema:
    """Retrieves a terminal along with its related gates"""
    try:
        terminal = await Terminals.objects.aget(id=terminal_id)
        gates = [gate async for gate in terminal.gates.all()]
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


async def update_terminal_service(
    terminal_id: int,
    data: TerminalUpdateSchema,
) -> TerminalOutSchema:
    """Updates an existing terminal"""
    try:
        # TODO: validate request.user has permission to update this terminal
        terminal = await Terminals.objects.aget(id=terminal_id)
        update_data = data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(terminal, field, value)
        await terminal.asave()
        return TerminalOutSchema.from_orm(terminal)
    except Terminals.DoesNotExist:
        raise NotFoundException("Terminal not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def delete_terminal_service(
    terminal_id: int,
) -> None:
    """Deletes a terminal"""
    try:
        # TODO: validate request.user has permission to delete this terminal
        terminal = await Terminals.objects.aget(id=terminal_id)
        await terminal.adelete()
    except Terminals.DoesNotExist:
        raise NotFoundException("Terminal not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


# ── Gates ──────────────────────────────────────────────────

async def create_gate_service(
    data: GateCreateSchema,
) -> GateOutSchema:
    """Creates a new gate under a terminal"""
    try:
        # TODO: validate request.user has permission to create gates
        # for this terminal's organization
        terminal_exists = await Terminals.objects.filter(
            id=data.terminal
        ).aexists()
        if not terminal_exists:
            raise NotFoundException("Terminal not found") from None

        gate = await Gates.objects.acreate(**data.dict())
        return GateOutSchema.from_orm(gate)
    except NotFoundException:
        raise
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def list_gates_service(
    terminal_id: int,
) -> list[GateOutSchema]:
    """Lists all gates for a given terminal"""
    try:
        # TODO: validate request.user belongs to the organization
        # that owns this terminal
        gates = Gates.objects.filter(terminal_id=terminal_id)
        return [GateOutSchema.from_orm(g) async for g in gates]
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def get_gate_service(
    gate_id: int,
) -> GateOutSchema:
    """Retrieves a single gate by id"""
    try:
        gate = await Gates.objects.aget(id=gate_id)
        return GateOutSchema.from_orm(gate)
    except Gates.DoesNotExist:
        raise NotFoundException("Gate not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def update_gate_service(
    gate_id: int,
    data: GateUpdateSchema,
) -> GateOutSchema:
    """Updates an existing gate"""
    try:
        # TODO: validate request.user has permission to update this gate
        gate = await Gates.objects.aget(id=gate_id)
        update_data = data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(gate, field, value)
        await gate.asave()
        return GateOutSchema.from_orm(gate)
    except Gates.DoesNotExist:
        raise NotFoundException("Gate not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e


async def delete_gate_service(
    gate_id: int,
) -> None:
    """Deletes a gate"""
    try:
        # TODO: validate request.user has permission to delete this gate
        gate = await Gates.objects.aget(id=gate_id)
        await gate.adelete()
    except Gates.DoesNotExist:
        raise NotFoundException("Gate not found") from None
    except Exception as e:
        raise BadRequestException(str(e)) from e
