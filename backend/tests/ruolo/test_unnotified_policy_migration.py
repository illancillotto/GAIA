import json
import os
import subprocess
import sys
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from alembic.util import load_python_file
from sqlalchemy import create_engine, inspect, text


def test_policy_scope_migration_preserves_existing_rules_and_roundtrips() -> None:
    versions = Path(__file__).resolve().parents[2] / "alembic" / "versions"
    revision = load_python_file(str(versions), "20261019_1400_tributi_unnotified_policy.py")
    engine = create_engine(os.environ.get("GAIA_MIGRATION_TEST_URL", "sqlite://"))
    with engine.begin() as connection:
        connection.execute(
            text(
                "CREATE TABLE ruolo_tributi_calculation_policies (id INTEGER PRIMARY KEY, name TEXT NOT NULL)"
            )
        )
        connection.execute(
            text("INSERT INTO ruolo_tributi_calculation_policies VALUES (1, 'Originale')")
        )
        with Operations.context(MigrationContext.configure(connection)):
            revision.upgrade()
        assert (
            connection.execute(
                text("SELECT only_unnotified FROM ruolo_tributi_calculation_policies WHERE id = 1")
            ).scalar_one()
            == 0
        )
        connection.execute(
            text(
                "INSERT INTO ruolo_tributi_calculation_policies (id, name, only_unnotified) VALUES (2, 'Limitata', TRUE)"
            )
        )
        assert (
            connection.execute(
                text("SELECT only_unnotified FROM ruolo_tributi_calculation_policies WHERE id = 2")
            ).scalar_one()
            == 1
        )
        with Operations.context(MigrationContext.configure(connection)):
            revision.downgrade()
        assert {
            column["name"]
            for column in inspect(connection).get_columns("ruolo_tributi_calculation_policies")
        } == {"id", "name"}
        assert connection.execute(
            text("SELECT name FROM ruolo_tributi_calculation_policies ORDER BY id")
        ).scalars().all() == ["Originale", "Limitata"]
    engine.dispose()


def test_isolated_release_and_future_merge_have_safe_upgrade_paths() -> None:
    script_path = Path(__file__).resolve().parents[2] / "alembic"
    process = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import json
import sys
from alembic.config import Config
from alembic.script import ScriptDirectory
config = Config()
config.set_main_option("script_location", sys.argv[1])
scripts = ScriptDirectory.from_config(config)
paths = [("20261019_1400", "20261005_1500"), ("heads", "20261019_1400"), ("heads", "20261007_1800")]
print(json.dumps([scripts.get_heads()] + [
    [step.revision.revision for step in scripts._upgrade_revs(target, current)]
    for target, current in paths
]))
""",
            str(script_path),
        ],
        capture_output=True,
        text=True,
        cwd=script_path.parent,
        check=False,
    )
    assert process.returncode == 0, process.stderr
    heads, isolated, remaining, current = json.loads(process.stdout)
    assert heads == ["20261019_1500"]
    assert isolated == ["20261019_1400"]
    assert remaining == [
        "20261006_1200",
        "20261007_1600",
        "20261007_1800",
        "20261019_1500",
    ]
    assert current == ["20261019_1400", "20261019_1500"]
    merge = load_python_file(str(script_path / "versions"), "20261019_1500_merge_tributi_policy.py")
    merge.upgrade()
    merge.downgrade()
