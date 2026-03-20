from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
DOCS = ROOT / "docs"


def test_required_root_files_exist() -> None:
    required_files = [
        ROOT / "README.md",
        ROOT / ".gitignore",
        ROOT / ".editorconfig",
        ROOT / ".env.example",
        ROOT / "Makefile",
        ROOT / "docker-compose.yml",
        ROOT / "docker-compose.override.yml",
    ]

    missing = [path.name for path in required_files if not path.exists()]
    assert not missing, f"Missing required files: {missing}"


def test_required_docs_exist() -> None:
    required_docs = [
        DOCS / "PRD.md",
        DOCS / "IMPLEMENTATION_PLAN.md",
        DOCS / "ARCHITECTURE.md",
        DOCS / "DEPLOYMENT.md",
        DOCS / "CODEX_PROMPT.md",
    ]

    missing = [path.name for path in required_docs if not path.exists()]
    assert not missing, f"Missing required docs: {missing}"


def test_backend_scaffold_contains_core_entrypoints() -> None:
    required_files = [
        BACKEND / "app" / "main.py",
        BACKEND / "app" / "api" / "routes" / "health.py",
        BACKEND / "alembic.ini",
        BACKEND / "alembic" / "env.py",
        BACKEND / "alembic" / "versions" / "20260319_0001_initial_schema.py",
    ]

    missing = [str(path.relative_to(ROOT)) for path in required_files if not path.exists()]
    assert not missing, f"Missing backend scaffold files: {missing}"


def test_frontend_scaffold_contains_base_routes() -> None:
    required_files = [
        FRONTEND / "package.json",
        FRONTEND / "src" / "app" / "layout.tsx",
        FRONTEND / "src" / "app" / "page.tsx",
        FRONTEND / "src" / "app" / "login" / "page.tsx",
        FRONTEND / "src" / "components" / "layout" / "app-shell.tsx",
    ]

    missing = [str(path.relative_to(ROOT)) for path in required_files if not path.exists()]
    assert not missing, f"Missing frontend scaffold files: {missing}"


def test_makefile_contains_expected_targets() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")

    for target in ["up:", "down:", "logs:", "rebuild:", "backend-shell:", "frontend-shell:", "migrate:"]:
        assert target in makefile


def test_compose_declares_expected_services() -> None:
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")

    for service_name in ["postgres:", "backend:", "frontend:", "nginx:"]:
        assert service_name in compose


def test_readme_mentions_quick_start_and_docs() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    for section in ["## Quick Start", "## Documentazione Disponibile", "## Stato Progetto"]:
        assert section in readme
