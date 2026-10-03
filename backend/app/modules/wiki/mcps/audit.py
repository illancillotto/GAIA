"""Bounded local history of synthetic tool calls, separate from application logs."""

import json
import re
import sqlite3
from pathlib import Path
from threading import RLock

from .docs.corpus import canonical_json, digest

AUDIT_SCOPE = "mcp.audit.read"
HISTORY_LIMIT = 1000


def audit_filter(key, value):
    if key in {"query", "cursor"}:
        return "[omesso]"
    if isinstance(value, str) and not re.fullmatch(
        r"(?:SYN-[A-Z0-9-]{1,64}|[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12})", value
    ):
        return "[omesso]"
    return value


class AuditStore:
    def __init__(self, path: Path):
        if path.is_symlink() or path.name != "gaia-mcp-audit.sqlite":
            raise ValueError("Only a dedicated gaia-mcp-audit.sqlite file is allowed")
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path, check_same_thread=False, timeout=10)
        path.chmod(0o600)
        self.lock = RLock()
        with self.connection:
            self.connection.execute(
                "CREATE TABLE IF NOT EXISTS calls "
                "(id INTEGER PRIMARY KEY, principal TEXT NOT NULL, scope TEXT NOT NULL, "
                "dataset TEXT NOT NULL, payload TEXT NOT NULL)"
            )

    def close(self):
        self.connection.close()

    def record(self, event, arguments, response):
        filters = {}
        if "error" not in response:
            filters = {key: audit_filter(key, value) for key, value in arguments.items()}
        payload = {"event": event, "filters": filters, "response": response}
        with self.lock, self.connection:
            self.connection.execute(
                "INSERT INTO calls (principal, scope, dataset, payload) VALUES (?, ?, ?, ?)",
                (
                    event["principal"],
                    event["permission_scope"] or "unknown",
                    event["dataset_or_corpus_version"],
                    canonical_json(payload),
                ),
            )
            self.connection.execute(
                "DELETE FROM calls WHERE id NOT IN (SELECT id FROM calls ORDER BY id DESC LIMIT ?)",
                (HISTORY_LIMIT,),
            )

    def history(self, context, dataset, *, before=0, limit=25):
        conditions = ["dataset=?", "(?=0 OR id<?)"]
        params = [dataset, before, before]
        if AUDIT_SCOPE not in context.scopes:
            conditions.append("principal=?")
            params.append(digest(context.principal.encode())[:24])
        scopes = sorted(context.scopes - {AUDIT_SCOPE, "docs.read"})
        conditions.append(f"scope IN ({','.join('?' for _ in scopes)})")
        params.extend(scopes)
        with self.lock:
            rows = self.connection.execute(
                "SELECT id, payload FROM calls WHERE "
                + " AND ".join(conditions)
                + " ORDER BY id DESC LIMIT ?",
                (*params, limit + 1),
            ).fetchall()
        return {
            "results": [{"id": row[0], **json.loads(row[1])} for row in rows[:limit]],
            "next_before": rows[limit - 1][0] if len(rows) > limit else None,
            "retention_limit": HISTORY_LIMIT,
            "visibility": "all_authorized" if AUDIT_SCOPE in context.scopes else "own",
        }
