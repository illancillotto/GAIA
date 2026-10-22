"""Integrity rules for STEP pages, schede and tributi (no browser access).

Every rule fails closed: a partial, repeated or inconsistent page aborts the
current scheda instead of storing incomplete data.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass


class StepIntegrityError(RuntimeError):
    """Data read from STEP is partial or inconsistent."""


def fingerprint(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()


def record_key(record: dict) -> str:
    if not record.get("COD_ENT") or not record.get("COD_FIS_NEW"):
        raise StepIntegrityError("Record STEP senza codice ente o codice fiscale")
    return f"{record['COD_ENT']}:{record['COD_FIS_NEW']}"


@dataclass(frozen=True)
class ListReference:
    total: int
    pages: int
    page_size: int
    fields: list

    @classmethod
    def from_first_page(cls, state: dict) -> ListReference:
        page_size = len(state["rows"])
        if (
            not page_size
            or state["page"] != 1
            or state["pages"] != math.ceil(state["total"] / page_size)
        ):
            raise StepIntegrityError("Paginazione elenco contribuenti STEP incoerente")
        return cls(
            total=state["total"], pages=state["pages"], page_size=page_size, fields=state["fields"]
        )

    def validate(self, state: dict) -> None:
        if state["total"] != self.total or state["pages"] != self.pages:
            raise StepIntegrityError(
                "Il totale dei contribuenti STEP e cambiato durante la lettura"
            )
        expected = min(self.page_size, self.total - (state["page"] - 1) * self.page_size)
        if len(state["rows"]) != expected:
            raise StepIntegrityError(
                f"Pagina STEP {state['page']}: {len(state['rows'])} righe, attese {expected}"
            )
        if state["fields"] != self.fields:
            raise StepIntegrityError("Le colonne dell'elenco contribuenti STEP sono cambiate")

    def page_of(self, index: int) -> int:
        return index // self.page_size + 1


@dataclass(frozen=True)
class DocumentEntry:
    grid: dict
    row_index: int
    document: dict


def _document_entries(grids: list[dict]) -> list[DocumentEntry]:
    if any(len(grid["rows"]) != grid["totalRows"] for grid in grids):
        raise StepIntegrityError("Una tabella della scheda STEP e caricata solo parzialmente")
    document_grids = [
        grid
        for grid in grids
        if {"NUM_DOC", "NUM_TRIB"} <= {field["name"] for field in grid["fields"]}
    ]
    if not document_grids:
        raise StepIntegrityError("Nessuna tabella documentale nella scheda STEP")
    entries = [
        DocumentEntry(grid=grid, row_index=index, document=document)
        for grid in document_grids
        for index, document in enumerate(grid["rows"])
    ]
    keys = {
        f"{entry.document.get('COD_ENT')}:{entry.document.get('NUM_DOC')}:{entry.document.get('PRG_COO')}"
        for entry in entries
    }
    if len(keys) != len(entries):
        raise StepIntegrityError("Documento duplicato nelle tabelle della scheda STEP")
    return entries


def sheet_documents(grids: list[dict], expected_count: object) -> tuple[list[DocumentEntry], dict]:
    """Documents from every document grid (Emessi, Presi in carico); the list count is a lower bound."""

    entries = _document_entries(grids)
    expected = int(expected_count) if str(expected_count).isdigit() else -1
    if expected < 0 or len(entries) < expected:
        raise StepIntegrityError(
            "Numero di documenti nella scheda STEP incoerente o caricamento parziale"
        )
    status = "matched" if expected == len(entries) else "detail_exceeds_list"
    return entries, {"listed": expected, "observed": len(entries), "status": status}


def expected_tributi(document: dict) -> int:
    raw = str(document.get("NUM_TRIB"))
    if not raw.isdigit():
        raise StepIntegrityError("Numero tributi STEP non valido")
    return int(raw)


@dataclass
class TributiCollector:
    """Accumulates the pages of the tributi modal of one document."""

    num_doc: str
    expected: int
    pages: int = 0
    page_size: int = 0

    def __post_init__(self) -> None:
        self.rows: list[dict] = []
        self.page_hashes: list[dict] = []

    def start(self, state: dict) -> None:
        self.pages = state["pages"]
        self.page_size = len(state["rows"])
        if (
            state["total"] != self.expected
            or not self.page_size
            or state["page"] != 1
            or self.pages != math.ceil(self.expected / self.page_size)
        ):
            raise StepIntegrityError(
                f"Tributi dichiarati {self.expected}, trovati {state['total']}: paginazione incoerente"
            )

    def add(self, state: dict | None, page_number: int) -> None:
        expected_rows = min(self.page_size, self.expected - len(self.rows))
        if (
            not state
            or state["page"] != page_number
            or state["total"] != self.expected
            or state["pages"] != self.pages
            or len(state["rows"]) != expected_rows
        ):
            raise StepIntegrityError(f"Pagina tributi STEP {page_number} incompleta o incoerente")
        digest = fingerprint(state["rows"])
        if any(item["sha256"] == digest for item in self.page_hashes):
            raise StepIntegrityError("Pagina tributi STEP ripetuta")
        if any(str(row.get("NUM_DOC")) != self.num_doc for row in state["rows"]):
            raise StepIntegrityError("Tributo STEP associato a un documento differente")
        self.rows.extend(state["rows"])
        self.page_hashes.append({"page": page_number, "rows": len(state["rows"]), "sha256": digest})

    def result(self) -> dict:
        if len(self.rows) != self.expected:
            raise StepIntegrityError("Totale tributi STEP estratti incoerente")
        return {"total": self.expected, "pages": self.page_hashes, "rows": self.rows}


def grid_link_selector(grid: dict, row: int, field: str) -> str:
    names = [candidate["name"] for candidate in grid["fields"]]
    if field not in names:
        raise StepIntegrityError(f"Colonna {field} non trovata nella tabella STEP")
    return f'a[onclick*="{grid["id"]}."][onclick*=",{row},{names.index(field)})"]'
