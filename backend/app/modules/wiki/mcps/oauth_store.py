"""Dedicated opaque OAuth grants; no passwords or plaintext tokens persisted."""

import hashlib
import json
import os
import secrets
import sqlite3
from pathlib import Path
from time import time

from .oauth_policy import OAuthPolicy


class GrantCapacityError(Exception):
    pass


def token_hash(token):
    return hashlib.sha256(token.encode()).hexdigest()


class GrantTransaction:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        self.owned = not self.connection.in_transaction
        if self.owned:
            self.connection.execute("BEGIN IMMEDIATE")
        return self

    def __exit__(self, exception_type, exception, traceback):
        if self.owned:
            self.connection.execute("COMMIT" if exception_type is None else "ROLLBACK")
        return False


class OAuthStore:
    def __init__(self, path: Path, *, policy=None):
        self.policy = policy or OAuthPolicy()
        if path.name != "gaia-mcp-oauth.sqlite" or path.is_symlink():
            raise ValueError("Dedicated OAuth database required")
        path.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(path, os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
        os.close(descriptor)
        path.chmod(0o600)
        self.connection = sqlite3.connect(path, timeout=10, isolation_level=None)
        self.connection.execute("PRAGMA journal_mode=DELETE")
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS grants "
            "(hash TEXT PRIMARY KEY, kind TEXT NOT NULL, family TEXT NOT NULL, "
            "expires REAL NOT NULL, payload TEXT NOT NULL)"
        )

    def close(self):
        self.connection.close()

    def transaction(self):
        return GrantTransaction(self.connection)

    def put(self, kind, payload, *, lifetime, family=None):
        with self.transaction():
            self.cleanup()
            self.check_capacity(payload.get("client_id"))
            token = secrets.token_urlsafe(32)
            self.connection.execute(
                "INSERT INTO grants VALUES (?, ?, ?, ?, ?)",
                (
                    token_hash(token),
                    kind,
                    family or secrets.token_hex(16),
                    min(time() + lifetime, payload.get("session_expires_at", float("inf"))),
                    json.dumps(payload),
                ),
            )
            return token

    def check_capacity(self, client_id):
        total, client_total = self.connection.execute(
            "SELECT COUNT(*), COALESCE(SUM(json_extract(payload, '$.client_id') = ?), 0) "
            "FROM grants",
            (client_id,),
        ).fetchone()
        if total >= self.policy.max_grants or client_total >= self.policy.max_client_grants:
            raise GrantCapacityError("OAuth grant capacity reached")

    def get(self, kind, token):
        row = self.connection.execute(
            "SELECT family, expires, payload FROM grants WHERE hash=? AND kind=? AND expires>?",
            (token_hash(token), kind, time()),
        ).fetchone()
        if row is None:
            return None
        return {"family": row[0], "expires_at": row[1], **json.loads(row[2])}

    def consume(self, kind, token, *, client_id=None):
        with self.transaction():
            grant = self.get(kind, token)
            if grant is None or (client_id is not None and grant["client_id"] != client_id):
                return None
            self.connection.execute(
                "UPDATE grants SET kind=? WHERE hash=? AND kind=?",
                ("used_" + kind, token_hash(token), kind),
            )
            return grant

    def revoke_by_family(self, family):
        self.connection.execute(
            "DELETE FROM grants WHERE family=? AND kind NOT LIKE 'used_%'", (family,)
        )

    def revoke(self, token):
        self.connection.execute(
            "DELETE FROM grants WHERE kind NOT LIKE 'used_%' AND "
            "family IN (SELECT family FROM grants WHERE hash=?)",
            (token_hash(token),),
        )

    def cleanup(self):
        self.connection.execute("DELETE FROM grants WHERE expires<=?", (time(),))

    def revoke_authorizations(self, *, subject=None, client_id=None):
        if subject is None and client_id is None:
            raise ValueError("Explicit revocation selector required")
        with self.transaction():
            return self.connection.execute(
                "DELETE FROM grants WHERE kind NOT LIKE 'used_%' AND family IN "
                "(SELECT family FROM grants WHERE "
                "(? IS NULL OR json_extract(payload, '$.subject')=?) AND "
                "(? IS NULL OR json_extract(payload, '$.client_id')=?))",
                (subject, subject, client_id, client_id),
            ).rowcount
