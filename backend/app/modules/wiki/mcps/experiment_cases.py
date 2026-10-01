"""New synthetic-only experiment protocol, independent of historical freezes."""

from dataclasses import dataclass

from .data.service import DataService, serialize_record

PROTOCOL = "gaia-synthetic-comparison-v1"
ANSWER_CONTRACT = (
    '\nRispondi solo con JSON: {"status":"found" oppure "absent",'
    '"records":[record richiesti con tutti i loro campi],'
    '"citations":[{"entity":"tabella","record_id":"UUID"}]}. '
    "Usa solo evidenze sintetiche; absent richiede una ricerca effettuata senza risultati."
)


@dataclass(frozen=True)
class ExperimentCase:
    id: str
    question: str
    entity: str
    expected: list[dict]


def synthetic_cases(service: DataService, count: int = 3) -> list[ExperimentCase]:
    if not 1 <= count <= 10:
        raise ValueError("Choose 1 to 10 synthetic subject lookups")
    subjects = service.connection.execute("SELECT * FROM subjects ORDER BY id LIMIT ?", (count,))
    cases = [
        ExperimentCase(
            f"subject-{index}",
            f"Restituisci il soggetto sintetico con UUID {row['id']} e tutti i suoi campi.",
            "subjects",
            [serialize_record(row)],
        )
        for index, row in enumerate(subjects)
    ]
    notice = service.connection.execute(
        "SELECT * FROM role_notices WHERE id IN (SELECT notice_id FROM payments) ORDER BY id LIMIT 1"
    ).fetchone()
    payments = service.connection.execute(
        "SELECT * FROM payments WHERE notice_id=? ORDER BY id", (notice["id"],)
    )
    cases.append(
        ExperimentCase(
            "payments",
            f"Trova l'avviso sintetico con codice {notice['notice_code']}, poi restituisci "
            "i suoi pagamenti con tutti i campi, non l'avviso.",
            "payments",
            [serialize_record(row) for row in payments],
        )
    )
    cases.append(
        ExperimentCase(
            "absent",
            "Cerca il soggetto sintetico con identificativo SYN-NOT-EXISTENT.",
            "subjects",
            [],
        )
    )
    return cases
