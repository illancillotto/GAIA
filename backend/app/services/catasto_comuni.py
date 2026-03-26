from __future__ import annotations

import re
import unicodedata

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.catasto import CatastoComune
from app.schemas.catasto import CatastoComuneUpsertRequest


DEFAULT_UFFICIO = "ORISTANO Territorio"
SEED_COMUNI: list[dict[str, str]] = [
    {"nome": "Terralba", "codice_sister": "L122#TERRALBA#2#2", "ufficio": DEFAULT_UFFICIO},
    {"nome": "Uras", "codice_sister": "L496#URAS#0#0", "ufficio": DEFAULT_UFFICIO},
    {"nome": "Marrubiu", "codice_sister": "E972#MARRUBIU#0#0", "ufficio": DEFAULT_UFFICIO},
    {"nome": "Narbolia", "codice_sister": "F840#NARBOLIA#0#0", "ufficio": DEFAULT_UFFICIO},
    {"nome": "Santa Giusta", "codice_sister": "I205#SANTA GIUSTA#0#0", "ufficio": DEFAULT_UFFICIO},
    {"nome": "Palmas Arborea", "codice_sister": "G286#PALMAS ARBOREA#0#0", "ufficio": DEFAULT_UFFICIO},
    {"nome": "Mogoro", "codice_sister": "F272#MOGORO#0#0", "ufficio": DEFAULT_UFFICIO},
    {"nome": "Zerfaliu", "codice_sister": "M168#ZERFALIU#0#0", "ufficio": DEFAULT_UFFICIO},
    {"nome": "Bauladu", "codice_sister": "A721#BAULADU#0#0", "ufficio": DEFAULT_UFFICIO},
    {"nome": "San Vero Milis", "codice_sister": "I384#SAN VERO MILIS#0#0", "ufficio": DEFAULT_UFFICIO},
    {"nome": "Tramatza", "codice_sister": "L321#TRAMATZA#0#0", "ufficio": DEFAULT_UFFICIO},
    {"nome": "Riola Sardo", "codice_sister": "H301#RIOLA SARDO#0#0", "ufficio": DEFAULT_UFFICIO},
    {"nome": "Nurachi", "codice_sister": "F980#NURACHI#0#0", "ufficio": DEFAULT_UFFICIO},
    {"nome": "Siamaggiore", "codice_sister": "I717#SIAMAGGIORE#0#0", "ufficio": DEFAULT_UFFICIO},
    {"nome": "Baratili San Pietro", "codice_sister": "A621#BARATILI SAN PIETRO#2#2", "ufficio": DEFAULT_UFFICIO},
    {"nome": "Ollastra", "codice_sister": "G043#OLLASTRA#0#0", "ufficio": DEFAULT_UFFICIO},
    {"nome": "Solarussa", "codice_sister": "I791#SOLARUSSA#0#0", "ufficio": DEFAULT_UFFICIO},
    {"nome": "Cabras", "codice_sister": "B314#CABRAS#2#2", "ufficio": DEFAULT_UFFICIO},
    {"nome": "Arborea", "codice_sister": "A357#ARBOREA#3#0", "ufficio": DEFAULT_UFFICIO},
    {"nome": "Simaxis", "codice_sister": "I743#SIMAXIS#2#2", "ufficio": DEFAULT_UFFICIO},
    {"nome": "Oristano", "codice_sister": "G113#ORISTANO#5#5", "ufficio": DEFAULT_UFFICIO},
    {"nome": "Zeddiani", "codice_sister": "M153#ZEDDIANI#0#0", "ufficio": DEFAULT_UFFICIO},
    {"nome": "Milis", "codice_sister": "F208#MILIS#0#0", "ufficio": DEFAULT_UFFICIO},
    {"nome": "San Nicolo d'Arcidano", "codice_sister": "A368#SAN NICOLO' D'ARCIDANO#0#0", "ufficio": DEFAULT_UFFICIO},
    {"nome": "Sili", "codice_sister": "G113#ORISTANO#5#5", "ufficio": DEFAULT_UFFICIO},
    {"nome": "Nuraxinieddu", "codice_sister": "G113#ORISTANO#5#5", "ufficio": DEFAULT_UFFICIO},
    {"nome": "Massama", "codice_sister": "G113#ORISTANO#5#5", "ufficio": DEFAULT_UFFICIO},
    {"nome": "Donigala", "codice_sister": "G113#ORISTANO#5#5", "ufficio": DEFAULT_UFFICIO},
]


class CatastoComuneConflictError(Exception):
    pass


class CatastoComuneNotFoundError(Exception):
    pass


def normalize_lookup_value(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", " ", normalized.lower()).strip()


def seed_catasto_comuni(db: Session) -> dict[str, int]:
    existing = {
        (item.nome, item.ufficio): item
        for item in db.scalars(select(CatastoComune)).all()
    }
    created = 0
    updated = 0
    for item in SEED_COMUNI:
        key = (item["nome"], item["ufficio"])
        current = existing.get(key)
        if current is None:
            db.add(CatastoComune(**item))
            created += 1
            continue

        if current.codice_sister != item["codice_sister"]:
            current.codice_sister = item["codice_sister"]
            updated += 1

    if created or updated:
        db.commit()

    return {
        "total": len(SEED_COMUNI),
        "created": created,
        "updated": updated,
    }


def ensure_seeded_comuni(db: Session) -> None:
    seed_catasto_comuni(db)


def list_catasto_comuni(db: Session, search: str | None = None) -> list[CatastoComune]:
    ensure_seeded_comuni(db)
    statement = select(CatastoComune)
    if search:
        statement = statement.where(func.lower(CatastoComune.nome).contains(search.strip().lower()))
    return list(db.scalars(statement.order_by(CatastoComune.nome.asc())).all())


def get_catasto_comune(db: Session, comune_id: int) -> CatastoComune:
    comune = db.get(CatastoComune, comune_id)
    if comune is None:
        raise CatastoComuneNotFoundError(f"Comune {comune_id} not found")
    return comune


def create_catasto_comune(db: Session, payload: CatastoComuneUpsertRequest) -> CatastoComune:
    existing = db.scalar(
        select(CatastoComune).where(
            func.lower(CatastoComune.nome) == payload.nome.strip().lower(),
            func.lower(CatastoComune.ufficio) == payload.ufficio.strip().lower(),
        )
    )
    if existing is not None:
        raise CatastoComuneConflictError("A comune with the same office already exists")

    comune = CatastoComune(
        nome=payload.nome.strip(),
        codice_sister=payload.codice_sister.strip(),
        ufficio=payload.ufficio.strip(),
    )
    db.add(comune)
    db.commit()
    db.refresh(comune)
    return comune


def update_catasto_comune(db: Session, comune_id: int, payload: CatastoComuneUpsertRequest) -> CatastoComune:
    comune = get_catasto_comune(db, comune_id)
    existing = db.scalar(
        select(CatastoComune).where(
            CatastoComune.id != comune_id,
            func.lower(CatastoComune.nome) == payload.nome.strip().lower(),
            func.lower(CatastoComune.ufficio) == payload.ufficio.strip().lower(),
        )
    )
    if existing is not None:
        raise CatastoComuneConflictError("A comune with the same office already exists")

    comune.nome = payload.nome.strip()
    comune.codice_sister = payload.codice_sister.strip()
    comune.ufficio = payload.ufficio.strip()
    db.commit()
    db.refresh(comune)
    return comune


def get_catasto_comuni_lookup(db: Session) -> dict[str, CatastoComune]:
    ensure_seeded_comuni(db)
    comuni = db.scalars(select(CatastoComune)).all()
    return {normalize_lookup_value(item.nome): item for item in comuni}
