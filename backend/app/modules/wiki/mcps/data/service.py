"""Authorized, bounded and audited reads from the synthetic dataset."""

from __future__ import annotations

import base64
import json
import logging
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from uuid import UUID

from pydantic import ValidationError

from ..context import CallContext
from ..docs.corpus import canonical_json, digest, estimated_tokens
from .database import open_readonly, read_manifest
from .inputs import INPUTS
from .queries import QUERIES, Query

logger = logging.getLogger(__name__)
SERVER_VERSION = "gaia-data-mcp-v1"


class SourceError(Exception):
    def __init__(self, code: str):
        self.code = code
        super().__init__(code)


def serialize_record(row: sqlite3.Row) -> dict:
    record = dict(row)
    for key in list(record):
        if key.endswith("_cents"):
            amount = record.pop(key)
            record[key.removesuffix("_cents")] = f"{amount // 100}.{amount % 100:02d}"
    return record


def encode_cursor(fingerprint: str, last_id: str) -> str:
    return base64.urlsafe_b64encode(
        canonical_json({"fingerprint": fingerprint, "last_id": last_id}).encode()
    ).decode()


def decode_cursor(cursor: str | None, fingerprint: str) -> str | None:
    if cursor is None:
        return None
    try:
        payload = json.loads(base64.b64decode(cursor, altchars=b"-_", validate=True))
        if set(payload) != {"fingerprint", "last_id"} or payload["fingerprint"] != fingerprint:
            raise ValueError("Cursor belongs to another query")
        return str(UUID(payload["last_id"]))
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise SourceError("INVALID_ARGUMENT") from exc


class DataService:
    def __init__(self, path: Path, audit=None):
        self.audit = audit
        self.connection = open_readonly(path)
        try:
            self.manifest = read_manifest(self.connection)
        except Exception:
            self.connection.close()
            raise

    def close(self) -> None:
        self.connection.close()

    def _read(self, query: Query, arguments: dict, fingerprint: str) -> tuple[list, str | None]:
        params = {key: value for key, value in arguments.items() if value is not None}
        limit = params.pop("limit", 1)
        cursor = params.pop("cursor", None)
        last_id = decode_cursor(cursor, fingerprint)
        if query.parent:
            table, parameter = query.parent
            exists = self.connection.execute(
                f"SELECT id FROM {table} WHERE id=?", (params[parameter],)
            ).fetchone()
            if exists is None:
                raise SourceError("NOT_FOUND")
        conditions = [condition for key, condition in query.filters.items() if key in params]
        if last_id:
            conditions.append("t.id>:last_id")
            params["last_id"] = last_id
        statement = query.select + "".join(f" AND {condition}" for condition in conditions)
        params["row_limit"] = limit + 1
        rows = self.connection.execute(
            statement + " ORDER BY t.id LIMIT :row_limit", params
        ).fetchall()
        if query.singleton and not rows:
            raise SourceError("NOT_FOUND")
        results = [serialize_record(row) for row in rows[:limit]]
        next_cursor = encode_cursor(fingerprint, results[-1]["id"]) if len(rows) > limit else None
        return results, next_cursor

    def _execute(
        self, tool_name: str, arguments: dict, context: CallContext
    ) -> tuple[list, str | None]:
        query = QUERIES.get(tool_name)
        if query is None:
            raise SourceError("INVALID_ARGUMENT")
        if query.scope not in context.scopes:
            raise SourceError("PERMISSION_DENIED")
        try:
            validated = INPUTS[tool_name].model_validate(arguments).model_dump(mode="json")
        except ValidationError as exc:
            code = (
                "RESULT_LIMIT_EXCEEDED"
                if any(
                    error["loc"] == ("limit",) and error["type"] == "less_than_equal"
                    for error in exc.errors()
                )
                else "INVALID_ARGUMENT"
            )
            raise SourceError(code) from exc
        filters = {key: value for key, value in validated.items() if key not in {"limit", "cursor"}}
        fingerprint = digest(
            canonical_json(
                {
                    "tool": tool_name,
                    "filters": filters,
                    "dataset": self.manifest["dataset_version"],
                    "principal": context.principal,
                }
            ).encode()
        )
        return self._read(query, validated, fingerprint)

    def call(self, tool_name: str, arguments: dict, context: CallContext) -> dict:
        started = perf_counter()
        response = {
            "tool": tool_name if tool_name in QUERIES else "unknown",
            "source": "gaia_synthetic_db",
            "results": [],
            "provenance": [],
            "result_count": 0,
            "truncated": False,
            "next_cursor": None,
            "request_id": context.request_id,
            "dataset_version": self.manifest["dataset_version"],
            "server_version": SERVER_VERSION,
        }
        try:
            results, cursor = self._execute(tool_name, arguments, context)
            response.update(
                results=results,
                result_count=len(results),
                truncated=cursor is not None,
                next_cursor=cursor,
            )
            response["provenance"] = [
                {
                    "source": "gaia_synthetic_db",
                    "entity": QUERIES[tool_name].entity,
                    "record_id": record["id"],
                    "dataset_version": response["dataset_version"],
                }
                for record in results
            ]
        except SourceError as exc:
            response["error"] = {"code": exc.code}
        except sqlite3.Error:
            response["error"] = {"code": "DATASET_UNAVAILABLE"}
        except Exception:
            response["error"] = {"code": "INTERNAL_ERROR"}
        response["estimated_tokens"] = estimated_tokens(canonical_json(response))
        event = {
            "timestamp": datetime.now(UTC).isoformat(),
            "request_id": context.request_id,
            "principal": digest(context.principal.encode())[:24],
            "experiment_run_id": context.experiment_run_id,
            "conversation_id": context.conversation_id,
            "tool_name": response["tool"],
            "source": response["source"],
            "duration_ms": round((perf_counter() - started) * 1000, 3),
            "status": "error" if "error" in response else "ok",
            "error": response.get("error"),
            "result_count": response["result_count"],
            "truncated": response["truncated"],
            "estimated_output_tokens": response["estimated_tokens"],
            "permission_scope": QUERIES[tool_name].scope if tool_name in QUERIES else None,
            "server_version": SERVER_VERSION,
            "dataset_or_corpus_version": response["dataset_version"],
        }
        logger.info("gaia_data_mcp_call", extra={"mcp_event": event})
        if self.audit is not None:
            self.audit.record(event, arguments, response)
        return response
