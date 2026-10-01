"""Fixed lexical RAG baseline rendered only from a verified synthetic database."""

import json
import re
import sqlite3

from .agent import bounded_evidence
from .context import CallContext
from .data.generator import TABLES
from .data.service import DataService, serialize_record
from .docs.corpus import canonical_json

EXPERIMENT_SCOPES = frozenset({"utenze.read", "catasto.read", "ruolo.read"})


class SyntheticStaticCorpus:
    def __init__(self, service: DataService, context: CallContext):
        if not EXPERIMENT_SCOPES <= context.scopes:
            raise PermissionError("The controlled comparison requires all synthetic data scopes")
        self.version = service.manifest["dataset_version"]
        self.connection = sqlite3.connect(":memory:")
        self.connection.execute(
            "CREATE VIRTUAL TABLE corpus USING fts5(text, entity UNINDEXED, record UNINDEXED)"
        )
        for table in TABLES:
            records = service.connection.execute(f"SELECT * FROM {table} ORDER BY id")
            self.connection.executemany(
                "INSERT INTO corpus VALUES (?, ?, ?)",
                [
                    (
                        canonical_json(serialize_record(row)),
                        table,
                        canonical_json(serialize_record(row)),
                    )
                    for row in records
                ],
            )

    def close(self):
        self.connection.close()

    def retrieve(self, question: str, budget: int) -> dict:
        identifiers = re.findall(
            r"\b(?:[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}|SYN-[\w-]+)\b",
            question,
            flags=re.IGNORECASE,
        )
        terms = identifiers or re.findall(r"[\w-]+", question)
        query = " OR ".join(f'"{term}"' for term in terms)
        rows = (
            self.connection.execute(
                "SELECT entity, record FROM corpus WHERE corpus MATCH ? ORDER BY rank, entity, record LIMIT 50",
                (query,),
            ).fetchall()
            if query
            else []
        )
        response = {
            "source": "gaia_synthetic_db",
            "results": [json.loads(row[1]) for row in rows],
            "provenance": [
                {
                    "source": "gaia_synthetic_db",
                    "entity": entity,
                    "record_id": json.loads(record)["id"],
                    "dataset_version": self.version,
                }
                for entity, record in rows
            ],
            "result_count": len(rows),
            "truncated": len(rows) == 50,
        }
        return bounded_evidence(response, budget)
