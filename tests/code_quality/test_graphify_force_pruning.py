import importlib.util
import runpy
import sys
import textwrap
from pathlib import Path
from types import ModuleType

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/patch_graphify_force_pruning.py"
SPEC = importlib.util.spec_from_file_location("patch_graphify_force_pruning", SCRIPT)
patcher = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(patcher)

PRUNING_BLOCK = """\
evict_sources = set(deleted_paths)
if changed_paths is not None:
    for p in extract_targets:
        try:
            evict_sources.add(str(p.relative_to(project_root)))
        except ValueError:
            evict_sources.add(str(p))
preserved_nodes = [
    node for node in existing
    if node["id"] not in new_ast_ids
    and (not evict_sources or node.get("source_file") not in evict_sources)
]
return preserved_nodes
"""


@pytest.fixture
def watch_path(tmp_path):
    path = tmp_path / "watch.py"
    path.write_text(textwrap.indent(PRUNING_BLOCK, " " * 16))
    return path


@pytest.mark.parametrize("force", [False, True])
@pytest.mark.parametrize("changed_paths", [None, [Path("services.py")]])
def test_force_prunes_removed_symbols_without_dropping_unrelated_nodes(
    watch_path, force, changed_paths
):
    assert patcher.patch_watch(watch_path) == "patched"
    block = textwrap.dedent(watch_path.read_text())
    namespace = {}
    source = (
        "def preserve(existing, new_ast_ids, deleted_paths, changed_paths, "
        "extract_targets, project_root, force):\n" + textwrap.indent(block, "    ")
    )
    exec(compile(source, str(watch_path), "exec"), namespace)
    existing = [
        {"id": "current", "source_file": "services.py"},
        {"id": "removed", "source_file": "services.py"},
        {"id": "other_code", "source_file": "other.py"},
        {"id": "semantic", "source_file": "runbook.md"},
    ]
    preserved = namespace["preserve"](
        existing,
        {"current"},
        set(),
        changed_paths,
        [Path("/code/services.py")],
        Path("/code"),
        force,
    )
    expected = [existing[2], existing[3]]
    if not force and changed_paths is None:
        expected.insert(0, existing[1])
    assert preserved == expected


def test_patch_is_idempotent(watch_path):
    assert patcher.patch_watch(watch_path) == "patched"
    patched = watch_path.read_bytes()
    assert patcher.patch_watch(watch_path) == "already patched"
    assert watch_path.read_bytes() == patched


@pytest.mark.parametrize(
    "content",
    [
        "unsupported version",
        patcher.TARGET * 2,
        patcher.REPLACEMENT * 2,
        patcher.TARGET + patcher.REPLACEMENT,
    ],
)
def test_unknown_or_ambiguous_upstream_layout_is_rejected_without_writing(watch_path, content):
    watch_path.write_text(content)
    with pytest.raises(ValueError, match="expected unique pruning block"):
        patcher.patch_watch(watch_path)
    assert watch_path.read_text() == content


def test_cli_patches_discovered_graphify_install(watch_path, monkeypatch, capsys):
    graphify = ModuleType("graphify")
    graphify.__file__ = str(watch_path.with_name("__init__.py"))
    monkeypatch.setitem(sys.modules, "graphify", graphify)
    with pytest.raises(SystemExit) as caught:
        runpy.run_path(str(SCRIPT), run_name="__main__")
    assert caught.value.code == 0
    assert f"patched: {watch_path}" in capsys.readouterr().out


@pytest.mark.parametrize(
    "failure", ["missing_package", "missing_watch", "unsupported_layout", "write_denied"]
)
def test_cli_reports_installation_errors(failure, watch_path, monkeypatch, capsys):
    graphify = ModuleType("graphify")
    graphify.__file__ = str(watch_path.with_name("__init__.py"))
    monkeypatch.setitem(sys.modules, "graphify", graphify)
    if failure == "missing_package":
        monkeypatch.setitem(sys.modules, "graphify", None)
    elif failure == "missing_watch":
        watch_path.unlink()
    elif failure == "unsupported_layout":
        watch_path.write_text("unsupported")
    else:

        def deny_write(*args, **kwargs):
            raise PermissionError("installation is read-only")

        monkeypatch.setattr(Path, "write_text", deny_write)
    assert patcher.main() == 1
    assert "graphify pruning patch failed:" in capsys.readouterr().err
