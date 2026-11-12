"""Read-only parcel history from imported tax rows, independent of the control index."""

from decimal import Decimal
from uuid import UUID

from sqlalchemy import String, case, cast, func, or_, select, tuple_

from app.modules.ruolo.models import RuoloAvviso, RuoloParticella, RuoloPartita
from app.modules.ruolo.services.parcel_control_identity import source_identity, token


def normalized(column, dialect):
    value = func.upper(func.trim(func.coalesce(column, "")))
    numeric = (
        value.op("~")("^[0-9]+$") if dialect == "postgresql" else ~value.op("GLOB")("*[^0-9]*")
    )
    return case(
        ((value != "") & numeric, func.coalesce(func.nullif(func.ltrim(value, "0"), ""), "0")),
        else_=value,
    )


def identity_columns(db):
    dialect = db.get_bind().dialect.name
    return [
        func.upper(func.trim(func.coalesce(RuoloPartita.comune_nome, ""))),
        func.upper(func.trim(func.coalesce(RuoloPartita.comune_codice, ""))),
        *(normalized(getattr(RuoloParticella, name), dialect) for name in ("foglio", "particella")),
        normalized(RuoloParticella.subalterno, dialect),
    ]


def rows_query():
    return (
        select(RuoloParticella, RuoloPartita, RuoloAvviso)
        .join(RuoloPartita, RuoloPartita.id == RuoloParticella.partita_id)
        .join(RuoloAvviso, RuoloAvviso.id == RuoloPartita.avviso_id)
    )


def escaped(value):
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def search_conditions(columns, filters):
    conditions = []
    if filters.comune:
        conditions.append(columns[0].ilike(f"%{escaped(filters.comune.upper())}%", escape="\\"))
    for column, value in ((columns[2], filters.foglio), (columns[3], filters.particella)):
        if value:
            conditions.append(column == token(value))
    if filters.search:
        conditions.append(
            or_(
                *(
                    column.ilike(f"%{escaped(filters.search)}%", escape="\\")
                    for column in (
                        RuoloAvviso.nominativo_raw,
                        RuoloAvviso.codice_fiscale_raw,
                        RuoloAvviso.codice_cnc,
                    )
                )
            )
        )
    return conditions


def list_row(row):
    return {
        "id": str(UUID(row.id)),
        "comune": row[0],
        "comune_codice": row[1],
        "foglio": row[2],
        "particella": row[3],
        "subalterno": row[4],
        "first_year": row.first_year,
        "last_year": row.last_year,
        "years_count": row.years_count,
    }


def list_parcels(db, filters):
    columns = identity_columns(db)
    # Incomplete identifiers remain separate records, never an inferred parcel.
    unresolved = case(
        (
            or_(columns[1] == "", columns[2] == "", columns[3] == ""),
            cast(RuoloParticella.id, String),
        ),
        else_="",
    )
    keys = [*columns, unresolved]
    conditions = search_conditions(columns, filters)
    selected = rows_query().with_only_columns(*keys).where(*conditions)
    # Select matching parcels first, then aggregate their entire imported history.
    grouped = rows_query().with_only_columns(
        *keys,
        func.min(cast(RuoloParticella.id, String)).label("id"),
        func.min(RuoloParticella.anno_tributario).label("first_year"),
        func.max(RuoloParticella.anno_tributario).label("last_year"),
        func.count(func.distinct(RuoloParticella.anno_tributario)).label("years_count"),
    )
    if conditions:
        grouped = grouped.where(tuple_(*keys).in_(selected))
    grouped = grouped.group_by(*keys).subquery()
    total = db.scalar(select(func.count()).select_from(grouped))
    records = db.execute(
        select(grouped)
        .order_by(*list(grouped.c)[:5], grouped.c.id)
        .offset((filters.page - 1) * filters.page_size)
        .limit(filters.page_size)
    ).all()
    return {
        "items": [list_row(row) for row in records],
        "total": total,
        "page": filters.page,
        "page_size": filters.page_size,
    }


def parcel_rows(db, identity):
    source = db.execute(rows_query().where(RuoloParticella.id == identity)).first()
    if source is None:
        raise LookupError("Particella non trovata")
    parcel, partita, _ = source
    reference = source_identity(parcel, partita)
    if reference["incomplete"]:
        return reference, [source]
    columns = identity_columns(db)
    values = db.execute(
        rows_query().with_only_columns(*columns).where(RuoloParticella.id == identity)
    ).one()
    rows = db.execute(
        rows_query()
        .where(*(column == value for column, value in zip(columns, values, strict=True)))
        .order_by(RuoloParticella.anno_tributario, RuoloAvviso.codice_cnc, RuoloParticella.id)
    ).all()
    return reference, rows


def tax_entry(parcel, partita, notice):
    amounts = [parcel.importo_manut, parcel.importo_irrig, parcel.importo_ist]
    return {
        "id": str(parcel.id),
        "year": parcel.anno_tributario,
        "notice_id": str(notice.id),
        "notice_number": notice.codice_cnc,
        "name": notice.nominativo_raw,
        "tax_code": notice.codice_fiscale_raw,
        "partita_tax_code": partita.contribuente_cf,
        "co_holders": partita.co_intestati_raw,
        "maintenance": amounts[0],
        "irrigation": amounts[1],
        "institutional": amounts[2],
        "total": sum(amounts, Decimal(0)) if all(value is not None for value in amounts) else None,
        "area_ha": parcel.sup_catastale_ha,
        "irrigated_ha": parcel.sup_irrigata_ha,
        "crop": parcel.coltura,
        "district": parcel.distretto,
        "catasto_id": str(parcel.cat_particella_id) if parcel.cat_particella_id else None,
    }


def history(db, identity: UUID, user_id: int):
    from .parcel_history_cadastre import cadastral_history

    reference, rows = parcel_rows(db, identity)
    entries = [tax_entry(*row) for row in rows]
    return {
        "id": str(identity),
        "reference": reference["reference"],
        "identity_incomplete": reference["incomplete"],
        "first_year": entries[0]["year"],
        "last_year": entries[-1]["year"],
        "taxes": entries,
        "cadastre": cadastral_history(db, rows, user_id),
    }
