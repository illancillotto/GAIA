"""Persistent fixed-window request budgets shared by a GAIA principal's clients."""

from time import time

from .oauth_store import token_hash


class PrincipalBudget:
    def __init__(self, store, requests, tools):
        self.store = store
        self.requests = requests
        self.tools = tools
        store.connection.execute(
            "CREATE TABLE IF NOT EXISTS connector_budget "
            "(principal TEXT PRIMARY KEY, window INTEGER, requests INTEGER, tools INTEGER)"
        )

    def admit(self, principal, tool_call):
        window = int(time() // 60)
        key = token_hash(principal)
        with self.store.transaction():
            connection = self.store.connection
            connection.execute("DELETE FROM connector_budget WHERE window<>?", (window,))
            row = connection.execute(
                "SELECT requests, tools FROM connector_budget WHERE principal=?", (key,)
            ).fetchone()
            requests, tools = row or (0, 0)
            if requests >= self.requests or (tool_call and tools >= self.tools):
                return False
            connection.execute(
                "INSERT OR REPLACE INTO connector_budget VALUES (?, ?, ?, ?)",
                (key, window, requests + 1, tools + int(tool_call)),
            )
            self.store.cleanup()
            return True
