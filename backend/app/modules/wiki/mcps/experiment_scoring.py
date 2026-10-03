"""Strict structured fact scoring; identity checks are not semantic entailment."""

import json
from typing import Literal

from pydantic import BaseModel, ConfigDict, ValidationError

from .data.queries import QUERIES
from .experiment_cases import ExperimentCase


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    entity: str
    record_id: str


class StructuredAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    status: Literal["found", "absent"]
    records: list[dict]
    citations: list[Citation]


def citation_validity(case: ExperimentCase, parsed: StructuredAnswer, evidence: list[dict]) -> bool:
    known = {
        (source["entity"], source["record_id"])
        for response in evidence
        for source in response.get("provenance", [])
        if source.get("source") == "gaia_synthetic_db"
    }
    cited = {(citation.entity, citation.record_id) for citation in parsed.citations}
    used = {(case.entity, record["id"]) for record in parsed.records}
    return all((cited <= known, cited == used, len(cited) == len(parsed.citations)))


def record_scores(case: ExperimentCase, records: list[dict]) -> dict:
    expected = {record["id"]: record for record in case.expected}
    actual = {record["id"]: record for record in records}
    facts = [
        actual.get(record_id, {}).get(field) == value
        for record_id, record in expected.items()
        for field, value in record.items()
    ]
    return {
        "identity_match": all((set(actual) == set(expected), len(actual) == len(records))),
        "facts_match": all(facts),
        "fields_match": all(
            set(record) == set(actual.get(record_id, {})) for record_id, record in expected.items()
        ),
        "fact_accuracy": sum(facts) / len(facts) if facts else None,
    }


def verified_absence(entity: str, evidence: list[dict]) -> bool:
    if not evidence or any("error" in response for response in evidence):
        return False
    final = evidence[-1]
    query = QUERIES.get(final.get("tool", ""))
    permitted = {entity} | {
        tool.parent[0] for tool in QUERIES.values() if tool.entity == entity and tool.parent
    }
    target = (
        query.entity in permitted
        if query
        else all(response.get("result_count") == 0 for response in evidence)
    )
    return all(
        (
            target,
            final.get("result_count") == 0,
            not final.get("truncated"),
            not final.get("next_cursor"),
        )
    )


def score_answer(case: ExperimentCase, answer: str, evidence: list[dict]) -> dict:
    try:
        parsed = StructuredAnswer.model_validate(json.loads(answer))
        if any(not isinstance(record.get("id"), str) for record in parsed.records):
            raise ValueError("Record identifiers must be strings")
    except (ValueError, ValidationError):
        return {"passed": False, "error": "INVALID_ANSWER"}
    scores = record_scores(case, parsed.records)
    citations = citation_validity(case, parsed, evidence)
    absent = verified_absence(case.entity, evidence)
    status = parsed.status == ("found" if case.expected else "absent")
    valid = all(
        (scores["identity_match"], scores["facts_match"], scores["fields_match"], citations, status)
    )
    passed = all((valid, bool(case.expected) or absent))
    return {
        "passed": passed,
        **scores,
        "citation_valid": citations,
        "no_answer_valid": all((absent, valid)) if not case.expected else None,
    }
