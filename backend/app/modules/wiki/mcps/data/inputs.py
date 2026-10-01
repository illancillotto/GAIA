"""Strict atomic tool inputs; authorization is never a model argument."""

from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Identifier = Annotated[UUID, Field(strict=False)]
Text = Annotated[str, Field(min_length=1, max_length=200)]
Year = Annotated[int, Field(ge=1900, le=2200)]


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class PageInput(Input):
    limit: int = Field(default=10, ge=1, le=25)
    cursor: str | None = Field(default=None, max_length=1200)


class SearchSubjects(PageInput):
    query: Text
    subject_type: Literal["person", "company"] | None = None


class GetSubject(Input):
    subject_id: Identifier


class SearchAccounts(PageInput):
    account_code: Text | None = None
    subject_id: Identifier | None = None
    district_code: Text | None = None
    campaign_year: Year | None = None
    status: Text | None = None


class GetAccount(Input):
    account_id: Identifier


class SearchParcels(PageInput):
    municipality_code: Text | None = None
    sheet: Text | None = None
    parcel_number: Text | None = None
    district_code: Text | None = None
    crop: Text | None = None


class GetParcel(Input):
    parcel_id: Identifier


class AccountsByParcel(GetParcel):
    year: Year
    limit: int = Field(default=20, ge=1, le=100)
    cursor: str | None = Field(default=None, max_length=1200)


class ParcelsByAccount(GetAccount):
    year: Year
    limit: int = Field(default=50, ge=1, le=100)
    cursor: str | None = Field(default=None, max_length=1200)


class SearchNotices(PageInput):
    subject_id: Identifier | None = None
    tax_year: Year | None = None
    status: Text | None = None
    account_code: Text | None = None


class GetNotice(Input):
    notice_id: Identifier


class PaymentsByNotice(GetNotice):
    limit: int = Field(default=20, ge=1, le=50)
    cursor: str | None = Field(default=None, max_length=1200)


class LinesByNotice(GetNotice):
    limit: int = Field(default=50, ge=1, le=100)
    cursor: str | None = Field(default=None, max_length=1200)


INPUTS = {
    "search_subjects": SearchSubjects,
    "get_subject": GetSubject,
    "search_irrigation_accounts": SearchAccounts,
    "get_irrigation_account": GetAccount,
    "search_parcels": SearchParcels,
    "get_parcel": GetParcel,
    "get_accounts_by_parcel": AccountsByParcel,
    "get_parcels_by_account": ParcelsByAccount,
    "search_role_notices": SearchNotices,
    "get_role_notice": GetNotice,
    "get_payments_by_notice": PaymentsByNotice,
    "get_role_lines_by_notice": LinesByNotice,
}
