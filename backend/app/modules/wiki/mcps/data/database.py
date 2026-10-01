"""Separate synthetic SQLite database with a read-only runtime connection."""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

from ..docs.corpus import canonical_json, digest
from .generator import GENERATOR_VERSION, TABLES, generate_dataset

SCHEMA_VERSION = 1


def validate_database_path(path: Path) -> Path:
    if (
        path.is_symlink()
        or not path.name.startswith("gaia-mcp-synthetic-")
        or path.suffix != ".sqlite"
    ):
        raise ValueError("Only a dedicated gaia-mcp-synthetic-*.sqlite database is allowed")
    return path.resolve()


def dataset_manifest(seed: str, data: dict[str, list[dict]]) -> dict:
    manifest = {
        "source": "gaia_synthetic_db",
        "schema_version": SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "seed": seed,
        "row_counts": {table: len(data[table]) for table in TABLES},
        "table_hashes": {
            table: digest(canonical_json(sorted(data[table], key=lambda row: row["id"])).encode())
            for table in TABLES
        },
    }
    manifest["dataset_version"] = digest(canonical_json(manifest).encode())
    return manifest


def seed_database(path: Path, seed: str) -> dict:
    path = validate_database_path(path)
    if path.exists():
        with closing(open_readonly(path)) as current:
            read_manifest(current)
    data = generate_dataset(seed)
    manifest = dataset_manifest(seed, data)
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name, dir=path.parent)
    os.close(descriptor)
    try:
        with closing(sqlite3.connect(temporary)) as connection, connection:
            connection.executescript(Path(__file__).with_name("schema.sql").read_text())
            for table in TABLES:
                columns = list(data[table][0])
                statement = f"INSERT INTO {table} ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})"
                connection.executemany(
                    statement, [tuple(row[column] for column in columns) for row in data[table]]
                )
            connection.execute(
                "INSERT INTO dataset_manifest VALUES (1, ?, ?, ?, ?, ?, ?)",
                (
                    manifest["source"],
                    SCHEMA_VERSION,
                    GENERATOR_VERSION,
                    seed,
                    manifest["dataset_version"],
                    canonical_json(manifest),
                ),
            )
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return manifest


def open_readonly(path: Path) -> sqlite3.Connection:
    path = validate_database_path(path)
    connection = sqlite3.connect(
        f"{path.as_uri()}?mode=ro&immutable=1", uri=True, check_same_thread=False
    )
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA query_only = ON")
    return connection


def read_manifest(connection: sqlite3.Connection) -> dict:
    row = connection.execute("SELECT * FROM dataset_manifest WHERE id = 1").fetchone()
    if (
        row is None
        or row["source"] != "gaia_synthetic_db"
        or row["schema_version"] != SCHEMA_VERSION
    ):
        raise ValueError("Unrecognized synthetic dataset")
    manifest = json.loads(row["manifest_json"])
    expected = dataset_manifest(
        manifest["seed"],
        {
            table: [
                dict(record) for record in connection.execute(f"SELECT * FROM {table} ORDER BY id")
            ]
            for table in TABLES
        },
    )
    if manifest != expected or row["dataset_version"] != expected["dataset_version"]:
        raise ValueError("Synthetic dataset integrity check failed")
    if connection.execute("PRAGMA foreign_key_check").fetchone() is not None:
        raise ValueError("Synthetic dataset has broken relationships")
    return manifest
