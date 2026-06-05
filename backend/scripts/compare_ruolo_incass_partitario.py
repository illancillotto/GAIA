from __future__ import annotations

import argparse
import csv
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.core.config import settings
from app.modules.ruolo.models import RuoloAvviso, RuoloParticella, RuoloPartita


_COMUNE_ALIASES = {
    "SILI'*ORISTANO": "SILI",
    "OLLASTRA SIMAXIS": "OLLASTRA",
    "SAN NICOLO ARCIDANO": "SAN NICOLO D'ARCIDANO",
}


@dataclass(frozen=True)
class ParcelKey:
    subject_id: str
    anno: int
    codice_partita: str
    comune_nome: str
    foglio: str
    particella: str
    subalterno: str


@dataclass
class ParcelSourceRow:
    source: str
    subject_id: str
    anno: int
    codice_partita: str
    comune_nome: str
    foglio: str
    particella: str
    subalterno: str
    avviso: str | None = None
    notice_id: str | None = None
    display_name: str | None = None

    @property
    def key(self) -> ParcelKey:
        return ParcelKey(
            subject_id=self.subject_id,
            anno=self.anno,
            codice_partita=self.codice_partita,
            comune_nome=self.comune_nome,
            foglio=self.foglio,
            particella=self.particella,
            subalterno=self.subalterno,
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Confronta le particelle Ruolo con il partitario inCass salvato in ana_payment_notices.",
    )
    parser.add_argument("--anno", type=int, default=2025, help="Annualita da confrontare.")
    parser.add_argument(
        "--output-dir",
        default=str(REPO_ROOT / "exports"),
        help="Directory dove scrivere summary/csv.",
    )
    return parser.parse_args()


def _candidate_db_urls(base_url: str) -> list[str]:
    candidates: list[str] = [base_url]
    try:
        parsed = make_url(base_url)
    except Exception:
        return candidates

    host = parsed.host or ""
    port = parsed.port
    if host == "postgres":
        for fallback_host in ("127.0.0.1", "localhost"):
            fallback_url = parsed.set(host=fallback_host, port=5434 if port in (None, 5432) else port)
            rendered = fallback_url.render_as_string(hide_password=False)
            if rendered not in candidates:
                candidates.append(rendered)
    return candidates


def _open_session() -> tuple[Session, str]:
    last_error: Exception | None = None
    for db_url in _candidate_db_urls(settings.database_url):
        engine = create_engine(db_url, pool_pre_ping=True)
        session_factory = sessionmaker(bind=engine, autoflush=False, autocommit=False)
        try:
            session = session_factory()
            session.execute(select(1))
            return session, db_url
        except Exception as exc:
            last_error = exc
            engine.dispose()
    raise RuntimeError("Impossibile connettersi al database con gli URL candidati.") from last_error


RUOLO_KEYS_SQL = """
SELECT DISTINCT
  av.subject_id::text AS subject_id,
  rp.anno_tributario AS anno,
  upper(regexp_replace(pt.codice_partita, E'\\s+', ' ', 'g')) AS codice_partita,
  upper(regexp_replace(pt.comune_nome, E'\\s+', ' ', 'g')) AS comune_nome,
  regexp_replace(rp.foglio, '[^0-9]', '', 'g')::int::text AS foglio,
  regexp_replace(rp.particella, '[^0-9]', '', 'g')::int::text AS particella,
  upper(coalesce(nullif(trim(rp.subalterno), ''), '')) AS subalterno,
  av.codice_cnc AS avviso,
  av.nominativo_raw AS display_name
FROM ruolo_particelle rp
JOIN ruolo_partite pt ON pt.id = rp.partita_id
JOIN ruolo_avvisi av ON av.id = pt.avviso_id
WHERE rp.anno_tributario = :anno
  AND av.subject_id IS NOT NULL
  AND rp.foglio ~ '[0-9]'
  AND rp.particella ~ '[0-9]'
"""


INCASS_KEYS_SQL = """
SELECT DISTINCT
  apn.subject_id::text AS subject_id,
  apn.anno::int AS anno,
  upper(regexp_replace(partita->>'codice_partita', E'\\s+', ' ', 'g')) AS codice_partita,
  upper(
    regexp_replace(
      CASE upper(regexp_replace(partita->>'comune_nome', E'\\s+', ' ', 'g'))
        WHEN 'SILI''*ORISTANO' THEN 'SILI'
        WHEN 'SILI`*ORISTANO' THEN 'SILI'
        WHEN 'ORISTANO*ORISTANO' THEN 'ORISTANO'
        WHEN 'SIMAXIS*SIMAXIS' THEN 'SIMAXIS'
        WHEN 'DONIGALA*ORISTANO' THEN 'DONIGALA'
        WHEN 'DONIGALA FENUGHEDU*ORISTANO' THEN 'DONIGALA'
        WHEN 'MASSAMA*ORISTANO' THEN 'MASSAMA'
        WHEN 'NURAXINIEDDU*ORISTANO' THEN 'NURAXINIEDDU'
        WHEN 'SOLANAS*CABRAS' THEN 'CABRAS'
        WHEN 'SAN VERO CONGIUS*SIMAXIS' THEN 'SIMAXIS'
        WHEN 'SAN VERO CONGIUS' THEN 'SIMAXIS'
        WHEN 'OLLASTRA SIMAXIS' THEN 'OLLASTRA'
        WHEN 'SAN NICOLO ARCIDANO' THEN 'SAN NICOLO D''ARCIDANO'
        ELSE partita->>'comune_nome'
      END,
      E'\\s+',
      ' ',
      'g'
    )
  ) AS comune_nome,
  regexp_replace(particella->>'foglio', '[^0-9]', '', 'g')::int::text AS foglio,
  regexp_replace(particella->>'particella', '[^0-9]', '', 'g')::int::text AS particella,
  upper(coalesce(nullif(trim(particella->>'subalterno'), ''), '')) AS subalterno,
  apn.source_notice_id AS notice_id,
  apn.display_name
FROM ana_payment_notices apn
CROSS JOIN LATERAL jsonb_array_elements(
  CASE
    WHEN apn.raw_detail_json::jsonb ? 'partitario' THEN apn.raw_detail_json::jsonb->'partitario'->'partite'
    WHEN apn.raw_detail_json::jsonb ? 'partite' THEN apn.raw_detail_json::jsonb->'partite'
    ELSE '[]'::jsonb
  END
) AS partita
CROSS JOIN LATERAL jsonb_array_elements(
  CASE
    WHEN jsonb_typeof(partita->'particelle') = 'array' THEN partita->'particelle'
    ELSE '[]'::jsonb
  END
) AS particella
WHERE apn.source_system = 'incass'
  AND apn.anno = :anno_text
  AND apn.subject_id IS NOT NULL
  AND apn.raw_detail_json IS NOT NULL
  AND regexp_replace(particella->>'foglio', '[^0-9]', '', 'g') <> ''
  AND regexp_replace(particella->>'particella', '[^0-9]', '', 'g') <> ''
"""


def _prepare_temp_tables(db: Session, anno: int) -> Counter[str]:
    stats = Counter()
    db.execute(text("DROP TABLE IF EXISTS tmp_ruolo_keys"))
    db.execute(text(f"CREATE TEMP TABLE tmp_ruolo_keys AS {RUOLO_KEYS_SQL}"), {"anno": anno})
    db.execute(text("CREATE INDEX ON tmp_ruolo_keys (subject_id, anno, codice_partita, comune_nome, foglio, particella, subalterno)"))

    db.execute(text("DROP TABLE IF EXISTS tmp_incass_keys"))
    db.execute(text(f"CREATE TEMP TABLE tmp_incass_keys AS {INCASS_KEYS_SQL}"), {"anno_text": str(anno)})
    db.execute(text("CREATE INDEX ON tmp_incass_keys (subject_id, anno, codice_partita, comune_nome, foglio, particella, subalterno)"))

    stats_row = db.execute(
        text(
            """
            SELECT
              (SELECT COUNT(*) FROM ruolo_particelle rp JOIN ruolo_partite pt ON pt.id = rp.partita_id JOIN ruolo_avvisi av ON av.id = pt.avviso_id WHERE rp.anno_tributario = :anno) AS ruolo_rows_total,
              (SELECT COUNT(*) FROM ruolo_particelle rp JOIN ruolo_partite pt ON pt.id = rp.partita_id JOIN ruolo_avvisi av ON av.id = pt.avviso_id WHERE rp.anno_tributario = :anno AND av.subject_id IS NULL) AS ruolo_rows_without_subject,
              (SELECT COUNT(*) FROM tmp_ruolo_keys) AS ruolo_distinct_keys,
              (SELECT COUNT(*) FROM ana_payment_notices WHERE source_system = 'incass' AND anno = :anno_text) AS incass_notices_total,
              (SELECT COUNT(*) FROM ana_payment_notices WHERE source_system = 'incass' AND anno = :anno_text AND subject_id IS NULL) AS incass_notices_without_subject,
              (SELECT COUNT(*) FROM ana_payment_notices WHERE source_system = 'incass' AND anno = :anno_text AND raw_detail_json IS NULL) AS incass_notices_without_detail,
              (SELECT COUNT(*) FROM ana_payment_notices WHERE source_system = 'incass' AND anno = :anno_text AND raw_detail_json IS NOT NULL AND NOT (raw_detail_json::jsonb ? 'partite' OR raw_detail_json::jsonb ? 'partitario')) AS incass_notices_without_partitario,
              (SELECT COUNT(DISTINCT notice_id) FROM tmp_incass_keys) AS incass_notices_with_partitario,
              (SELECT COUNT(*) FROM tmp_incass_keys) AS incass_distinct_keys
            """
        ),
        {"anno": anno, "anno_text": str(anno)},
    ).mappings().one()
    for key, value in stats_row.items():
        stats[key] = int(value or 0)
    return stats


def _top_counts(db: Session, sql: str) -> list[tuple[str, int]]:
    rows = db.execute(text(sql)).all()
    return [(str(row[0]), int(row[1])) for row in rows]


def _write_query_to_csv(db: Session, path: Path, sql: str) -> int:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = None
        result = db.execute(text(sql))
        count = 0
        for mapping in result.mappings():
            if writer is None:
                writer = csv.DictWriter(handle, fieldnames=list(mapping.keys()))
                writer.writeheader()
            writer.writerow(dict(mapping))
            count += 1
        return count


def _normalize_spaces(value: str | None) -> str:
    if not value:
        return ""
    return " ".join(value.strip().upper().split())


def _normalize_comune(value: str | None) -> str:
    normalized = _normalize_spaces(value)
    return _COMUNE_ALIASES.get(normalized, normalized)


def _normalize_partita(value: str | None) -> str:
    return _normalize_spaces(value)


def _normalize_number_token(value: str | None) -> str:
    if not value:
        return ""
    cleaned = "".join(ch for ch in value.strip() if ch.isdigit())
    if not cleaned:
        return _normalize_spaces(value)
    return str(int(cleaned))


def _normalize_subalterno(value: str | None) -> str:
    return _normalize_spaces(value)


def _extract_partitario_payload(raw_detail_json: Any) -> dict[str, Any] | None:
    if not isinstance(raw_detail_json, dict):
        return None
    nested = raw_detail_json.get("partitario")
    if isinstance(nested, dict):
        return nested
    if isinstance(raw_detail_json.get("partite"), list):
        return raw_detail_json
    return None


def load_ruolo_rows(db: Session, anno: int) -> tuple[list[ParcelSourceRow], Counter[str]]:
    rows = db.execute(
        select(RuoloParticella, RuoloPartita, RuoloAvviso)
        .join(RuoloPartita, RuoloPartita.id == RuoloParticella.partita_id)
        .join(RuoloAvviso, RuoloAvviso.id == RuoloPartita.avviso_id)
        .where(RuoloParticella.anno_tributario == anno)
    ).all()

    result: list[ParcelSourceRow] = []
    stats: Counter[str] = Counter()
    for particella, partita, avviso in rows:
        stats["ruolo_rows_total"] += 1
        if avviso.subject_id is None:
            stats["ruolo_rows_without_subject"] += 1
            continue
        result.append(
            ParcelSourceRow(
                source="ruolo",
                subject_id=str(avviso.subject_id),
                anno=anno,
                codice_partita=_normalize_partita(partita.codice_partita),
                comune_nome=_normalize_comune(partita.comune_nome),
                foglio=_normalize_number_token(particella.foglio),
                particella=_normalize_number_token(particella.particella),
                subalterno=_normalize_subalterno(particella.subalterno),
                avviso=avviso.codice_cnc,
                display_name=avviso.nominativo_raw,
            )
        )
    return result, stats


def load_incass_rows(db: Session, anno: int) -> tuple[list[ParcelSourceRow], Counter[str]]:
    stats_row = db.execute(
        text(
            """
            SELECT
              COUNT(*) AS total_notices,
              COUNT(*) FILTER (WHERE subject_id IS NULL) AS notices_without_subject,
              COUNT(*) FILTER (
                WHERE raw_detail_json IS NULL
                   OR NOT (
                     raw_detail_json::jsonb ? 'partite'
                     OR raw_detail_json::jsonb ? 'partitario'
                   )
              ) AS notices_without_partitario,
              COUNT(*) FILTER (
                WHERE subject_id IS NOT NULL
                  AND raw_detail_json IS NOT NULL
                  AND (
                    raw_detail_json::jsonb ? 'partite'
                    OR raw_detail_json::jsonb ? 'partitario'
                  )
              ) AS notices_with_partitario
            FROM ana_payment_notices
            WHERE source_system = 'incass' AND anno = :anno
            """
        ),
        {"anno": str(anno)},
    ).mappings().one()

    rows = db.execute(
        text(
            """
            SELECT
              subject_id::text AS subject_id,
              source_notice_id,
              display_name,
              CASE
                WHEN raw_detail_json IS NULL THEN NULL
                WHEN raw_detail_json::jsonb ? 'partitario' THEN raw_detail_json::jsonb -> 'partitario' -> 'partite'
                WHEN raw_detail_json::jsonb ? 'partite' THEN raw_detail_json::jsonb -> 'partite'
                ELSE NULL
              END AS partite
            FROM ana_payment_notices
            WHERE source_system = 'incass'
              AND anno = :anno
              AND subject_id IS NOT NULL
              AND raw_detail_json IS NOT NULL
              AND (
                raw_detail_json::jsonb ? 'partite'
                OR raw_detail_json::jsonb ? 'partitario'
              )
            """
        ),
        {"anno": str(anno)},
    ).mappings().all()

    result: list[ParcelSourceRow] = []
    stats: Counter[str] = Counter(
        {
            "incass_notices_total": int(stats_row["total_notices"] or 0),
            "incass_notices_without_subject": int(stats_row["notices_without_subject"] or 0),
            "incass_notices_without_partitario": int(stats_row["notices_without_partitario"] or 0),
            "incass_notices_with_partitario": int(stats_row["notices_with_partitario"] or 0),
        }
    )
    for row in rows:
        partite = row["partite"]
        if not isinstance(partite, list):
            stats["incass_notices_with_invalid_partitario"] += 1
            continue

        for partita in partite:
            if not isinstance(partita, dict):
                continue
            codice_partita = _normalize_partita(partita.get("codice_partita"))
            comune_nome = _normalize_comune(partita.get("comune_nome"))
            particelle = partita.get("particelle")
            if not isinstance(particelle, list):
                continue
            for particella in particelle:
                if not isinstance(particella, dict):
                    continue
                result.append(
                    ParcelSourceRow(
                        source="incass",
                        subject_id=row["subject_id"],
                        anno=anno,
                        codice_partita=codice_partita,
                        comune_nome=comune_nome,
                        foglio=_normalize_number_token(particella.get("foglio")),
                        particella=_normalize_number_token(particella.get("particella")),
                        subalterno=_normalize_subalterno(particella.get("subalterno")),
                        notice_id=row["source_notice_id"],
                        display_name=row["display_name"],
                    )
                )
    return result, stats


def dedupe_rows(rows: list[ParcelSourceRow]) -> tuple[dict[ParcelKey, ParcelSourceRow], Counter[str]]:
    deduped: dict[ParcelKey, ParcelSourceRow] = {}
    stats: Counter[str] = Counter()
    for row in rows:
        stats[f"{row.source}_rows_comparable"] += 1
        if not row.foglio or not row.particella or not row.codice_partita or not row.comune_nome:
            stats[f"{row.source}_rows_incomplete_key"] += 1
            continue
        if row.key in deduped:
            stats[f"{row.source}_duplicate_keys"] += 1
            continue
        deduped[row.key] = row
    return deduped, stats


def write_csv(path: Path, rows: list[ParcelSourceRow]) -> None:
    fieldnames = [
        "source",
        "subject_id",
        "anno",
        "codice_partita",
        "comune_nome",
        "foglio",
        "particella",
        "subalterno",
        "avviso",
        "notice_id",
        "display_name",
    ]
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "source": row.source,
                    "subject_id": row.subject_id,
                    "anno": row.anno,
                    "codice_partita": row.codice_partita,
                    "comune_nome": row.comune_nome,
                    "foglio": row.foglio,
                    "particella": row.particella,
                    "subalterno": row.subalterno,
                    "avviso": row.avviso,
                    "notice_id": row.notice_id,
                    "display_name": row.display_name,
                }
            )


def write_summary(
    path: Path,
    *,
    anno: int,
    stats: Counter[str],
    missing_in_incass: list[ParcelSourceRow],
    missing_in_ruolo: list[ParcelSourceRow],
) -> None:
    top_missing_in_incass = Counter(row.comune_nome for row in missing_in_incass).most_common(20)
    top_missing_in_ruolo = Counter(row.comune_nome for row in missing_in_ruolo).most_common(20)

    lines = [
        f"# Confronto Ruolo vs inCass partitario - {anno}",
        "",
        "## Sintesi",
        "",
        f"- Righe ruolo anno: `{stats['ruolo_rows_total']}`",
        f"- Righe ruolo senza `subject_id` escluse: `{stats['ruolo_rows_without_subject']}`",
        f"- Righe ruolo comparabili: `{stats['ruolo_rows_comparable']}`",
        f"- Chiavi ruolo distinte: `{stats['ruolo_distinct_keys']}`",
        f"- Notice inCass anno: `{stats['incass_notices_total']}`",
        f"- Notice inCass senza `subject_id`: `{stats['incass_notices_without_subject']}`",
        f"- Notice inCass senza partitario: `{stats['incass_notices_without_partitario']}`",
        f"- Notice inCass con partitario: `{stats['incass_notices_with_partitario']}`",
        f"- Righe partitario comparabili: `{stats['incass_rows_comparable']}`",
        f"- Chiavi inCass distinte: `{stats['incass_distinct_keys']}`",
        f"- Chiavi presenti in entrambi: `{stats['keys_in_both']}`",
        f"- Chiavi presenti solo in ruolo: `{len(missing_in_incass)}`",
        f"- Chiavi presenti solo in inCass: `{len(missing_in_ruolo)}`",
        "",
        "## Top comuni solo in ruolo",
        "",
    ]

    if top_missing_in_incass:
        lines.extend([f"- `{comune}`: `{count}`" for comune, count in top_missing_in_incass])
    else:
        lines.append("- Nessuno")

    lines.extend(["", "## Top comuni solo in inCass", ""])
    if top_missing_in_ruolo:
        lines.extend([f"- `{comune}`: `{count}`" for comune, count in top_missing_in_ruolo])
    else:
        lines.append("- Nessuno")

    lines.extend(
        [
            "",
            "## File generati",
            "",
            f"- `ruolo_incass_partitario_{anno}_missing_in_incass.csv`",
            f"- `ruolo_incass_partitario_{anno}_missing_in_ruolo.csv`",
        ]
    )

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    args = parse_args()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    db, resolved_db_url = _open_session()
    try:
        stats = _prepare_temp_tables(db, args.anno)

        intersection_count = db.execute(
            text(
                """
                SELECT COUNT(*)
                FROM tmp_ruolo_keys rk
                INNER JOIN tmp_incass_keys ik
                  USING (subject_id, anno, codice_partita, comune_nome, foglio, particella, subalterno)
                """
            )
        ).scalar_one()
        stats["keys_in_both"] = int(intersection_count or 0)

        missing_in_incass_sql = """
            SELECT rk.*
            FROM tmp_ruolo_keys rk
            LEFT JOIN tmp_incass_keys ik
              USING (subject_id, anno, codice_partita, comune_nome, foglio, particella, subalterno)
            WHERE ik.subject_id IS NULL
            ORDER BY rk.comune_nome, rk.codice_partita, rk.foglio, rk.particella, rk.subalterno
        """
        missing_in_ruolo_sql = """
            SELECT ik.*
            FROM tmp_incass_keys ik
            LEFT JOIN tmp_ruolo_keys rk
              USING (subject_id, anno, codice_partita, comune_nome, foglio, particella, subalterno)
            WHERE rk.subject_id IS NULL
            ORDER BY ik.comune_nome, ik.codice_partita, ik.foglio, ik.particella, ik.subalterno
        """

        missing_in_incass_path = output_dir / f"ruolo_incass_partitario_{args.anno}_missing_in_incass.csv"
        missing_in_ruolo_path = output_dir / f"ruolo_incass_partitario_{args.anno}_missing_in_ruolo.csv"
        summary_path = output_dir / f"ruolo_incass_partitario_{args.anno}_summary.md"

        missing_in_incass_count = _write_query_to_csv(db, missing_in_incass_path, missing_in_incass_sql)
        missing_in_ruolo_count = _write_query_to_csv(db, missing_in_ruolo_path, missing_in_ruolo_sql)

        top_missing_in_incass = _top_counts(
            db,
            """
            SELECT comune_nome, COUNT(*)
            FROM (
              SELECT rk.*
              FROM tmp_ruolo_keys rk
              LEFT JOIN tmp_incass_keys ik
                USING (subject_id, anno, codice_partita, comune_nome, foglio, particella, subalterno)
              WHERE ik.subject_id IS NULL
            ) q
            GROUP BY comune_nome
            ORDER BY COUNT(*) DESC, comune_nome
            LIMIT 20
            """,
        )
        top_missing_in_ruolo = _top_counts(
            db,
            """
            SELECT comune_nome, COUNT(*)
            FROM (
              SELECT ik.*
              FROM tmp_incass_keys ik
              LEFT JOIN tmp_ruolo_keys rk
                USING (subject_id, anno, codice_partita, comune_nome, foglio, particella, subalterno)
              WHERE rk.subject_id IS NULL
            ) q
            GROUP BY comune_nome
            ORDER BY COUNT(*) DESC, comune_nome
            LIMIT 20
            """,
        )
    finally:
        bind = db.get_bind()
        db.close()
        bind.dispose()

    lines = [
        f"# Confronto Ruolo vs inCass partitario - {args.anno}",
        "",
        "## Sintesi",
        "",
        f"- Righe ruolo anno: `{stats['ruolo_rows_total']}`",
        f"- Righe ruolo senza `subject_id` escluse: `{stats['ruolo_rows_without_subject']}`",
        f"- Chiavi ruolo distinte: `{stats['ruolo_distinct_keys']}`",
        f"- Notice inCass anno: `{stats['incass_notices_total']}`",
        f"- Notice inCass senza `subject_id`: `{stats['incass_notices_without_subject']}`",
        f"- Notice inCass senza `raw_detail_json`: `{stats['incass_notices_without_detail']}`",
        f"- Notice inCass senza partitario strutturato: `{stats['incass_notices_without_partitario']}`",
        f"- Notice inCass con partitario: `{stats['incass_notices_with_partitario']}`",
        f"- Chiavi inCass distinte: `{stats['incass_distinct_keys']}`",
        f"- Chiavi presenti in entrambi: `{stats['keys_in_both']}`",
        f"- Chiavi presenti solo in ruolo: `{missing_in_incass_count}`",
        f"- Chiavi presenti solo in inCass: `{missing_in_ruolo_count}`",
        "",
        "## Top comuni solo in ruolo",
        "",
    ]
    lines.extend([f"- `{comune}`: `{count}`" for comune, count in top_missing_in_incass] or ["- Nessuno"])
    lines.extend(["", "## Top comuni solo in inCass", ""])
    lines.extend([f"- `{comune}`: `{count}`" for comune, count in top_missing_in_ruolo] or ["- Nessuno"])
    lines.extend(["", "## File generati", "", f"- `{missing_in_incass_path.name}`", f"- `{missing_in_ruolo_path.name}`"])
    summary_path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(
        f"anno={args.anno} ruolo_keys={stats['ruolo_distinct_keys']} incass_keys={stats['incass_distinct_keys']} "
        f"both={stats['keys_in_both']} only_ruolo={missing_in_incass_count} only_incass={missing_in_ruolo_count}"
    )
    print(f"database_url={resolved_db_url}")
    print(f"summary={summary_path}")
    print(f"missing_in_incass={missing_in_incass_path}")
    print(f"missing_in_ruolo={missing_in_ruolo_path}")


if __name__ == "__main__":
    main()
