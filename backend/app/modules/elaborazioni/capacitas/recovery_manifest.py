from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class RecoveryManifest:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(path)
        self.connection.row_factory = sqlite3.Row
        self.connection.execute("PRAGMA journal_mode=WAL")
        self.connection.execute(
            "CREATE TABLE IF NOT EXISTS tasks ("
            "task_key TEXT PRIMARY KEY, subject_id TEXT NOT NULL, stage TEXT NOT NULL, "
            "payload TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending', "
            "attempts INTEGER NOT NULL DEFAULT 0, result TEXT, error TEXT)"
        )
        self.connection.commit()

    def add(self, subject_id, stage, key, payload, *, commit=True):
        self.connection.execute(
            "INSERT OR IGNORE INTO tasks(task_key,subject_id,stage,payload) VALUES(?,?,?,?)",
            (f"{subject_id}:{stage}:{key}", str(subject_id), stage, json.dumps(payload)),
        )
        if commit:
            self.connection.commit()

    def next_task(self, priority_subject=None):
        row = self.connection.execute(
            "SELECT * FROM tasks WHERE status='pending' "
            "ORDER BY subject_id=? DESC, subject_id, stage, task_key LIMIT 1",
            (str(priority_subject),),
        ).fetchone()
        if row is None:
            return None
        task = dict(row)
        task["payload"] = json.loads(task["payload"])
        return task

    def finish(self, task, *, result=None, error=None):
        self.connection.execute(
            "UPDATE tasks SET status=?,attempts=attempts+1,result=?,error=? WHERE task_key=?",
            (
                "failed" if error is not None else "succeeded",
                json.dumps(result),
                error,
                task["task_key"],
            ),
        )
        self.connection.commit()

    def retry_failed(self):
        self.connection.execute("UPDATE tasks SET status='pending' WHERE status='failed'")
        self.connection.commit()

    def summary(self):
        rows = self.connection.execute(
            "SELECT stage,status,count(*) AS count FROM tasks GROUP BY stage,status"
        ).fetchall()
        return [dict(row) for row in rows]

    def close(self):
        self.connection.close()
