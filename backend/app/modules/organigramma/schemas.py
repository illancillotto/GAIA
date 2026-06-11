from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator

OrgUnitTypeLiteral = Literal["direzione", "distretto", "settore", "squadra"]
SourceLiteral = Literal["manuale", "whitecompany", "bridge_team"]
TargetTypeLiteral = Literal["user", "org_unit"]
ScopeLiteral = Literal["read", "approve", "full"]
ViaLiteral = Literal["gerarchia", "override"]
OrgRevisionStatusLiteral = Literal["published", "archived", "draft"]
OrgDraftStatusLiteral = Literal["draft", "published", "discarded"]
OrgChangeEntityTypeLiteral = Literal["draft", "unit", "assignment", "override"]
OrgChangeActionLiteral = Literal[
    "draft_created",
    "published",
    "discarded",
    "create",
    "move",
    "relink",
    "detach",
    "assign",
    "unassign",
    "update",
    "delete",
]


# --------------------------------------------------------------------------- #
# Persone (riferimento leggero, NON un ruolo RBAC editabile da qui)
# --------------------------------------------------------------------------- #
class PersonRef(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    user_id: int = Field(validation_alias="id", serialization_alias="user_id")
    full_name: str | None = None
    username: str
    email: str
    rbac_role: str = Field(validation_alias="role", serialization_alias="rbac_role")
    is_active: bool


# --------------------------------------------------------------------------- #
# Org unit
# --------------------------------------------------------------------------- #
class OrgUnitBase(BaseModel):
    nome: str = Field(min_length=1, max_length=200)
    tipo: OrgUnitTypeLiteral
    parent_id: UUID | None = None
    is_active: bool = True
    sort_order: int = 0
    canvas_x: int = 0
    canvas_y: int = 0
    source: SourceLiteral = "manuale"
    wc_area_id: UUID | None = None
    legacy_team_id: UUID | None = None


class OrgUnitCreate(OrgUnitBase):
    pass


class OrgUnitUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=1, max_length=200)
    tipo: OrgUnitTypeLiteral | None = None
    parent_id: UUID | None = None
    is_active: bool | None = None
    sort_order: int | None = None
    canvas_x: int | None = None
    canvas_y: int | None = None
    source: SourceLiteral | None = None
    wc_area_id: UUID | None = None
    legacy_team_id: UUID | None = None


class OrgUnitResponse(OrgUnitBase):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    updated_at: datetime


class OrgUnitTreeNode(BaseModel):
    id: UUID
    nome: str
    tipo: OrgUnitTypeLiteral
    parent_id: UUID | None
    source: SourceLiteral
    canvas_x: int
    canvas_y: int
    wc_area_id: UUID | None = None
    legacy_team_id: UUID | None = None
    is_active: bool
    sort_order: int
    person_count: int
    child_count: int
    children: list["OrgUnitTreeNode"] = Field(default_factory=list)


# --------------------------------------------------------------------------- #
# Assignment
# --------------------------------------------------------------------------- #
class OrgAssignmentBase(BaseModel):
    user_id: int
    org_unit_id: UUID
    manager_user_id: int | None = None
    title: str | None = Field(default=None, max_length=150)
    is_primary: bool = False
    active: bool = True
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    source: SourceLiteral = "manuale"
    wc_operator_id: UUID | None = None


class OrgAssignmentCreate(OrgAssignmentBase):
    pass


class OrgAssignmentUpdate(BaseModel):
    org_unit_id: UUID | None = None
    manager_user_id: int | None = None
    title: str | None = Field(default=None, max_length=150)
    is_primary: bool | None = None
    active: bool | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    source: SourceLiteral | None = None
    wc_operator_id: UUID | None = None


class OrgAssignmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: int
    org_unit_id: UUID
    manager_user_id: int | None
    title: str | None
    is_primary: bool
    active: bool
    valid_from: datetime | None
    valid_to: datetime | None
    source: SourceLiteral
    wc_operator_id: UUID | None
    created_at: datetime
    updated_at: datetime
    person: PersonRef | None = None
    manager: PersonRef | None = None


# --------------------------------------------------------------------------- #
# Visibility override
# --------------------------------------------------------------------------- #
class OrgVisibilityOverrideBase(BaseModel):
    viewer_user_id: int
    target_type: TargetTypeLiteral
    target_user_id: int | None = None
    target_org_unit_id: UUID | None = None
    scope: ScopeLiteral
    motivo: str | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    is_active: bool = True

    @model_validator(mode="after")
    def _check_target_coherence(self) -> "OrgVisibilityOverrideBase":
        # CHECK applicativo: esattamente uno tra target_user_id/target_org_unit_id,
        # coerente con target_type.
        if self.target_type == "user":
            if self.target_user_id is None or self.target_org_unit_id is not None:
                raise ValueError("target_type 'user' richiede solo target_user_id valorizzato")
        else:  # org_unit
            if self.target_org_unit_id is None or self.target_user_id is not None:
                raise ValueError("target_type 'org_unit' richiede solo target_org_unit_id valorizzato")
        return self


class OrgVisibilityOverrideCreate(OrgVisibilityOverrideBase):
    pass


class OrgVisibilityOverrideUpdate(BaseModel):
    scope: ScopeLiteral | None = None
    motivo: str | None = None
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    is_active: bool | None = None


class OrgVisibilityOverrideResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    viewer_user_id: int
    target_type: TargetTypeLiteral
    target_user_id: int | None
    target_org_unit_id: UUID | None
    scope: ScopeLiteral
    motivo: str | None
    valid_from: datetime | None
    valid_to: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    status: Literal["attivo", "programmato", "scaduto", "disattivato"] | None = None
    viewer: PersonRef | None = None
    target_label: str | None = None


# --------------------------------------------------------------------------- #
# Unit detail
# --------------------------------------------------------------------------- #
class UnitDetailResponse(BaseModel):
    unit: OrgUnitResponse
    path: list[OrgUnitResponse]
    responsabile: PersonRef | None = None
    responsabile_title: str | None = None
    assignments: list[OrgAssignmentResponse]


# --------------------------------------------------------------------------- #
# Visibility simulator ("Chi vede chi")
# --------------------------------------------------------------------------- #
class VisibleUnit(BaseModel):
    org_unit_id: UUID
    nome: str
    tipo: OrgUnitTypeLiteral
    parent_id: UUID | None
    via: ViaLiteral
    scope: ScopeLiteral | None = None


class VisiblePerson(BaseModel):
    user_id: int
    full_name: str | None
    title: str | None
    org_unit_id: UUID | None = None
    via: ViaLiteral


class VisibilityResult(BaseModel):
    viewer: PersonRef
    full: bool
    units: list[VisibleUnit]
    people: list[VisiblePerson]


class WhiteCompanySyncResult(BaseModel):
    units_created: int = 0
    units_updated: int = 0
    units_skipped_locked: int = 0
    assignments_created: int = 0
    assignments_updated: int = 0
    assignments_skipped_locked: int = 0
    message: str = ""


# --------------------------------------------------------------------------- #
# Revisioni e bozze
# --------------------------------------------------------------------------- #
class OrgRevisionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    label: str
    status: OrgRevisionStatusLiteral
    notes: str | None = None
    source_revision_id: UUID | None = None
    created_by_user_id: int | None = None
    published_by_user_id: int | None = None
    created_at: datetime
    published_at: datetime | None = None


class OrgDraftCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    notes: str | None = None


class OrgDraftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    status: OrgDraftStatusLiteral
    notes: str | None = None
    base_revision_id: UUID
    working_revision_id: UUID
    created_by_user_id: int | None = None
    updated_by_user_id: int | None = None
    published_by_user_id: int | None = None
    created_at: datetime
    updated_at: datetime
    published_at: datetime | None = None


class OrgDraftDetailResponse(OrgDraftResponse):
    event_count: int = 0
    unit_count: int = 0
    assignment_count: int = 0


class OrgChangeEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    draft_id: UUID
    entity_type: OrgChangeEntityTypeLiteral
    entity_id: UUID
    action: OrgChangeActionLiteral
    before_json: dict | None = None
    after_json: dict | None = None
    changed_by_user_id: int | None = None
    changed_at: datetime


OrgUnitTreeNode.model_rebuild()
