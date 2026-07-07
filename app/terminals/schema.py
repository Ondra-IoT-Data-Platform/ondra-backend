from datetime import datetime
from uuid import UUID

from ninja import ModelSchema, Schema

from terminals.models import Gates, Terminals


############# Terminals #########################

class TerminalCreateSchema(ModelSchema):
    class Meta:
        model = Terminals
        fields = ["name", "location", "longitude", "latitude", "status"]


class TerminalUpdateSchema(ModelSchema):
    class Meta:
        model = Terminals
        fields = ["name", "location", "longitude", "latitude", "status"]
        fields_optional = "__all__"


class TerminalOutSchema(ModelSchema):
    class Meta:
        model = Terminals
        fields = [
            "id",
            "name",
            "location",
            "longitude",
            "latitude",
            "organization",
            "status",
            "created_at",
            "updated_at",
        ]


################# Gates #################

class GateCreateSchema(ModelSchema):
    class Meta:
        model = Gates
        fields = ["terminal", "name", "gate_type"]


class GateUpdateSchema(ModelSchema):
    class Meta:
        model = Gates
        fields = ["name", "gate_type"]
        fields_optional = "__all__"


class GateOutSchema(ModelSchema):
    class Meta:
        model = Gates
        fields = ["id", "terminal", "name", "gate_type"]


########## Nested / composite schemas #################

class GateNestedOutSchema(Schema):
    """Lightweight gate representation nested inside a terminal response."""
    id: int
    name: str
    gate_type: str


class TerminalWithGatesOutSchema(ModelSchema):
    """Terminal output including its related gates."""
    gates: list[GateNestedOutSchema] = []

    class Meta:
        model = Terminals
        fields = [
            "id",
            "name",
            "location",
            "longitude",
            "latitude",
            "organization",
            "status",
            "created_at",
            "updated_at",
        ]
