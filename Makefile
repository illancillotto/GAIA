COMPOSE = docker compose
GRAPHIFY_ENV = if [ -f /home/cbo/CursorProjects/GAIA/.env.graphify ]; then set -a; . /home/cbo/CursorProjects/GAIA/.env.graphify; set +a; fi;
GRAPHIFY_CODE_FLAGS ?=
# gpt-5.4-mini e' stato ritirato dal codex-lb il 2026-09-09: rispondeva HTTP 503
# no_plan_support_for_model, e graphify degradava a "partial results" con exit 0,
# cioe' un grafo aggiornato ma senza arricchimento semantico. gpt-reserve e' il
# modello veloce del catalogo attuale, validato su elaborazioni, presenze e wiki
# (quest'ultimo e' il corpus con l'hang storico su gpt-5.5: nessun hang).
# I timeout sono allineati ai valori con cui la validazione e' passata.
GRAPHIFY_DOC_MODEL ?= gpt-reserve
GRAPHIFY_WIKI_DOC_MODEL = $(GRAPHIFY_DOC_MODEL)
GRAPHIFY_WIKI_DOC_FLAGS = --max-concurrency 1 --api-timeout 180
GRAPHIFY_WIKI_DOC_TIMEOUT = timeout --foreground 420s
GRAPHIFY_WIKI_DOC_DEBUG_FLAGS = --max-concurrency 1 --api-timeout 30
GRAPHIFY_WIKI_DOC_DEBUG_TIMEOUT = timeout --foreground 90s
GRAPHIFY_WIKI_DOC_DEBUG_LOG = /tmp/graphify-wiki-docs-debug.log
GRAPHIFY_PRESENZE_DOC_MODEL = $(GRAPHIFY_DOC_MODEL)
GRAPHIFY_PRESENZE_DOC_FLAGS = --max-concurrency 1 --api-timeout 180
GRAPHIFY_PRESENZE_DOC_TIMEOUT = timeout --foreground 420s
GRAPHIFY_UTENZE_DOC_MODEL = $(GRAPHIFY_DOC_MODEL)
GRAPHIFY_UTENZE_DOC_FLAGS = --max-concurrency 1 --api-timeout 180
GRAPHIFY_UTENZE_DOC_TIMEOUT = timeout --foreground 420s
GRAPHIFY_PLATFORM_DOC_MODEL = $(GRAPHIFY_DOC_MODEL)
GRAPHIFY_PLATFORM_DOC_FLAGS = --max-concurrency 1 --api-timeout 180
GRAPHIFY_ELABORAZIONI_DOC_MODEL = $(GRAPHIFY_DOC_MODEL)
GRAPHIFY_ELABORAZIONI_DOC_FLAGS = --max-concurrency 1 --api-timeout 180
GRAPHIFY_ELABORAZIONI_DOC_TIMEOUT = timeout --foreground 420s
QUALITY_PYTHON ?= python3
WORKER_PYTHON ?= backend/.venv/bin/python
WORKER_COVERAGE_JSON ?= backend/coverage-worker.json
WORKER_COVERAGE_XML ?= backend/coverage-worker.xml
MCP_DOCS_MANIFEST ?= config/mcps/docs-manifest.json
MCP_DOCS_OUTPUT ?= runtime-data/mcps/docs
MCP_DATA_DATABASE ?= runtime-data/mcps/data/gaia-mcp-synthetic-v1.sqlite
MCP_AUDIT_DATABASE ?= runtime-data/mcps/audit/gaia-mcp-audit.sqlite
GAIA_SYNTHETIC_SEED ?= gaia-v1
PRESENZE_IDENTITY_MANIFEST ?= secrets/presenze/canonical-identities.json
PRESENZE_IDENTITY_AUDIT_USER_ID ?= 1

.PHONY: test-ruolo-postgres test-presenze-postgres audit-presenze-identities
.PHONY: mcp-docs-build mcp-docs-serve test-mcp-docs
.PHONY: mcp-data-seed mcp-data-reset mcp-data-serve mcp-http test-mcp mcp-evaluate
.PHONY: mcp-data-http
.PHONY: graphify-elaborazioni-worker-code graphify-elaborazioni-worker-query graphify-elaborazioni-docs graphify-elaborazioni-docs-query

.PHONY: up down logs rebuild backend-shell frontend-shell migrate bootstrap-admin bootstrap-domain bootstrap-sections purge-seed live-sync scheduled-live-sync local-gateway-up local-gateway-down wiki-index wiki-reindex test test-worker test-wiki coverage-wiki smoke-network-vpn-bypass backup-db-to-nas restore-db-from-nas lint lint-backend lint-backend-all style-ratchet format-backend lint-frontend complexity-report complexity-check complexity-changed complexity-ratchet complexity-baseline complexity-baseline-verify complexity-ci-gate quality-test graphify-patch-openai-base-url graphify-refresh-core-code graphify-refresh-core-docs graphify-refresh-core graphify-catasto-code graphify-catasto-docs graphify-catasto-query graphify-presenze-code graphify-presenze-docs graphify-presenze-query graphify-inaz-code graphify-inaz-docs graphify-inaz-query graphify-network-code graphify-network-docs graphify-network-query graphify-operazioni-code graphify-operazioni-docs graphify-operazioni-query graphify-organigramma-code graphify-organigramma-docs graphify-organigramma-query graphify-riordino-code graphify-riordino-docs graphify-riordino-query graphify-ruolo-code graphify-ruolo-docs graphify-ruolo-query graphify-utenze-code graphify-utenze-docs graphify-utenze-query graphify-wiki-code graphify-wiki-docs graphify-wiki-docs-debug graphify-wiki-query graphify-backend graphify-backend-query graphify-frontend graphify-frontend-query graphify-docs graphify-docs-query graphify-platform-docs graphify-platform-docs-query graphify-query

up:
	$(COMPOSE) up -d

down:
	$(COMPOSE) down

logs:
	$(COMPOSE) logs -f --tail=200

rebuild:
	$(COMPOSE) up -d --build

backend-shell:
	$(COMPOSE) exec backend /bin/sh

frontend-shell:
	$(COMPOSE) exec frontend /bin/sh

migrate:
	$(COMPOSE) exec backend alembic upgrade head

bootstrap-admin:
	$(COMPOSE) exec backend python -m app.scripts.bootstrap_admin

bootstrap-sections:
	$(COMPOSE) exec backend python -m app.scripts.bootstrap_sections

bootstrap-domain:
	$(COMPOSE) exec backend python scripts/bootstrap_domain.py

purge-seed:
	$(COMPOSE) exec backend python scripts/purge_seed_data.py

live-sync:
	$(COMPOSE) exec backend python scripts/live_sync.py

scheduled-live-sync:
	$(COMPOSE) exec backend python scripts/scheduled_live_sync.py

local-gateway-up:
	LOCAL_DEV_GATEWAY_PORT=$${LOCAL_DEV_GATEWAY_PORT:-80} docker compose -f docker-compose.local-gateway.yml up -d

local-gateway-down:
	docker compose -f docker-compose.local-gateway.yml down

wiki-index:
	$(COMPOSE) exec backend python -m app.modules.wiki.services.indexer

mcp-docs-build:
	PYTHONPATH=backend $(QUALITY_PYTHON) -m app.modules.wiki.mcps.docs build --root . --manifest "$(MCP_DOCS_MANIFEST)" --output "$(MCP_DOCS_OUTPUT)"

mcp-docs-serve:
	PYTHONPATH=backend $(QUALITY_PYTHON) -m app.modules.wiki.mcps.docs serve --corpus "$(MCP_DOCS_OUTPUT)/corpus.json"

test-mcp-docs:
	$(QUALITY_PYTHON) -m pytest backend/tests/test_wiki_docs_mcp.py --cov=app.modules.wiki.mcps.docs --cov-branch --cov-report=term-missing:skip-covered --cov-fail-under=100

mcp-data-seed:
	PYTHONPATH=backend $(QUALITY_PYTHON) -m app.modules.wiki.mcps.data seed --database "$(MCP_DATA_DATABASE)" --seed "$(GAIA_SYNTHETIC_SEED)"

mcp-data-reset: mcp-data-seed

mcp-data-serve:
	PYTHONPATH=backend $(QUALITY_PYTHON) -m app.modules.wiki.mcps.data serve --database "$(MCP_DATA_DATABASE)"

mcp-http:
	PYTHONPATH=backend $(QUALITY_PYTHON) -m app.modules.wiki.mcps --corpus "$(MCP_DOCS_OUTPUT)/corpus.json" --database "$(MCP_DATA_DATABASE)"

mcp-data-http:
	PYTHONPATH=backend $(QUALITY_PYTHON) -m app.modules.wiki.mcps --data-only --database "$(MCP_DATA_DATABASE)" --audit-database "$(MCP_AUDIT_DATABASE)"

test-mcp:
	$(QUALITY_PYTHON) -m pytest backend/tests/test_wiki_docs_mcp.py backend/tests/test_wiki_data_mcp.py backend/tests/test_wiki_mcp_http.py backend/tests/test_wiki_mcp_integration.py backend/tests/test_wiki_mcp_evaluation.py backend/tests/test_wiki_mcp_experiment.py backend/tests/test_wiki_mcp_console.py backend/tests/test_wiki_mcp_discovery.py backend/tests/test_wiki_mcp_oauth.py backend/tests/test_wiki_mcp_connector.py --cov=app.modules.wiki.mcps --cov=app.modules.wiki.router --cov-branch --cov-report=term-missing:skip-covered --cov-report=json:backend/coverage-mcp.json --cov-fail-under=100

.PHONY: test-mcp-oauth
test-mcp-oauth:
	$(QUALITY_PYTHON) -m pytest backend/tests/test_wiki_mcp_oauth.py --cov=app.modules.wiki.mcps.oauth_store --cov=app.modules.wiki.mcps.oauth_policy --cov=app.modules.wiki.mcps.oauth_provider --cov=app.modules.wiki.mcps.oauth_http --cov=app.modules.wiki.mcps.oauth_gaia --cov-branch --cov-report=term-missing --cov-report=json:/tmp/gaia-mcp-oauth-coverage.json --cov-fail-under=100

.PHONY: mcp-connector test-mcp-connector test-mcp-consent
mcp-connector:
	PYTHONPATH=backend $(QUALITY_PYTHON) -m uvicorn app.modules.wiki.mcps.connector:create_configured_app --factory --host 127.0.0.1 --port 8769 --no-access-log

test-mcp-connector:
	$(QUALITY_PYTHON) -m pytest backend/tests/test_wiki_mcp_connector.py backend/tests/test_wiki_mcp_oauth.py --cov=app.modules.wiki.mcps.connector --cov=app.modules.wiki.mcps.connector_config --cov=app.modules.wiki.mcps.connector_budget --cov=app.modules.wiki.mcps.oauth_provider --cov=app.modules.wiki.mcps.oauth_policy --cov=app.modules.wiki.mcps.oauth_maintenance --cov=app.modules.wiki.mcps.oauth_admin --cov-branch --cov-report=term-missing --cov-report=json:/tmp/gaia-connector-coverage.json --cov-fail-under=100

test-mcp-consent:
	cd frontend && VITEST_COVERAGE_INCLUDE='src/features/wiki/mcp-consent.tsx,src/features/wiki/mcp-consent-api.ts,src/app/mcp/consent/page.tsx' npm run test:coverage -- tests/unit/mcp-consent.test.tsx --coverage.reportsDirectory=/tmp/gaia-mcp-consent-frontend-coverage

.PHONY: test-mcp-discovery
test-mcp-discovery:
	$(QUALITY_PYTHON) -m pytest backend/tests/test_wiki_mcp_discovery.py backend/tests/test_wiki_data_mcp.py::test_sdk_handlers_and_stdio_runner --cov=app.modules.wiki.mcps.data.server --cov=app.modules.wiki.mcps.data.catalog --cov-branch --cov-report=term-missing --cov-fail-under=100

.PHONY: mcp-comparison-plan mcp-comparison-live
mcp-comparison-plan:
	PYTHONPATH=backend $(QUALITY_PYTHON) -m app.modules.wiki.mcps.experiment_cli --database "$(MCP_DATA_DATABASE)" --output runtime-data/mcps/evaluation/comparison.jsonl

mcp-comparison-live:
	PYTHONPATH=backend $(QUALITY_PYTHON) -m app.modules.wiki.mcps.experiment_cli --database "$(MCP_DATA_DATABASE)" --output runtime-data/mcps/evaluation/comparison.jsonl --live

mcp-evaluate:
	PYTHONPATH=backend $(QUALITY_PYTHON) -m app.modules.wiki.mcps.evaluation docs --artifact "$(MCP_DOCS_OUTPUT)/corpus.json" --queries config/mcps/docs-queries.json --output runtime-data/mcps/evaluation/docs.json
	PYTHONPATH=backend $(QUALITY_PYTHON) -m app.modules.wiki.mcps.evaluation data --artifact "$(MCP_DATA_DATABASE)" --queries config/mcps/data-queries.json --output runtime-data/mcps/evaluation/data.json

wiki-reindex:
	$(COMPOSE) exec backend python -c "from app.core.database import SessionLocal; from app.modules.wiki.services.indexer import index_documents; db=SessionLocal(); index_documents(db, force=True); db.close(); print('Reindex completato')"

test:
	$(COMPOSE) exec backend python -m pytest

test-worker:
	@set -eu; \
	root="$$(pwd)"; \
	worker_dir="$$root/modules/elaborazioni/worker"; \
	python="$(WORKER_PYTHON)"; \
	case "$$python" in /*) ;; */*) python="$$root/$$python" ;; esac; \
	coverage_json="$(WORKER_COVERAGE_JSON)"; \
	coverage_xml="$(WORKER_COVERAGE_XML)"; \
	case "$$coverage_json" in /*) ;; *) coverage_json="$$root/$$coverage_json" ;; esac; \
	case "$$coverage_xml" in /*) ;; *) coverage_xml="$$root/$$coverage_xml" ;; esac; \
	data_dir="$$(mktemp -d /tmp/gaia-worker-coverage.XXXXXX)"; \
	trap 'rm -rf "$$data_dir"' EXIT INT TERM; \
	find "$$worker_dir/tests" -maxdepth 1 -type f -name 'test_*.py' -print | sort > "$$data_dir/test-files"; \
	test -s "$$data_dir/test-files"; \
	export PYTHONPATH="$$root/backend:$$worker_dir$${PYTHONPATH:+:$$PYTHONPATH}"; \
	export COVERAGE_FILE="$$data_dir/.coverage"; \
	while IFS= read -r test_file; do \
		relative_test="$${test_file#$$worker_dir/}"; \
		echo "==> worker $$relative_test"; \
		(cd "$$worker_dir" && "$$python" -m coverage run --branch --parallel-mode --source="$$worker_dir" --omit="$$worker_dir/tests/*" -m pytest -q -o cache_dir="$$data_dir/pytest-cache" "$$relative_test"); \
	done < "$$data_dir/test-files"; \
	"$$python" -m coverage combine "$$data_dir"; \
	mkdir -p "$$(dirname "$$coverage_json")" "$$(dirname "$$coverage_xml")"; \
	"$$python" -m coverage json -o "$$coverage_json"; \
	"$$python" -m coverage xml -o "$$coverage_xml"; \
	"$$python" -m coverage report

test-ruolo-postgres:
	$(COMPOSE) exec backend sh -lc 'GAIA_TEST_POSTGRES_URL="$${DATABASE_URL}" python -m pytest -m postgres tests/ruolo/test_tributi_notice_registry_postgres.py tests/ruolo/test_tributi_notice_migration_postgres.py'

test-presenze-postgres:
	$(COMPOSE) exec backend sh -lc 'GAIA_TEST_POSTGRES_URL="$${DATABASE_URL}" python -m pytest -m postgres tests/test_presenze_mapping_postgres.py'

audit-presenze-identities:
	@test -f "$(PRESENZE_IDENTITY_MANIFEST)" || { \
		echo "Errore: registro canonico locale non trovato: $(PRESENZE_IDENTITY_MANIFEST)" >&2; \
		exit 2; \
	}
	@container_manifest="/tmp/gaia-presenze-canonical-identities-audit.json"; \
	trap '$(COMPOSE) exec -T backend find /tmp -maxdepth 1 -type f -name "$${container_manifest##*/}" -delete >/dev/null 2>&1 || true' EXIT INT TERM; \
	$(COMPOSE) cp "$(PRESENZE_IDENTITY_MANIFEST)" "backend:$$container_manifest" >/dev/null; \
	$(COMPOSE) exec -T backend python scripts/backfill_presenze_canonical_identities.py \
		"$$container_manifest" \
		--changed-by-gaia-user-id "$(PRESENZE_IDENTITY_AUDIT_USER_ID)" \
		--reason "Audit read-only registro canonico locale" \
		--require-unchanged

test-wiki:
	$(COMPOSE) exec backend python -m pytest tests/test_wiki_indexer.py tests/test_wiki_rag.py tests/test_wiki_requests_api.py tests/test_wiki_articles_api.py tests/test_wiki_chat_api.py -v

coverage-wiki:
	$(COMPOSE) exec backend python -m pytest tests/test_wiki_indexer.py tests/test_wiki_rag.py tests/test_wiki_requests_api.py tests/test_wiki_articles_api.py tests/test_wiki_chat_api.py --cov=app/modules/wiki --cov-report=term-missing --cov-report=html:htmlcov/wiki

smoke-network-vpn-bypass:
	./scripts/smoke-network-vpn-bypass.sh

backup-db-to-nas:
	./scripts/export-gaia-db-to-nas.sh

restore-db-from-nas:
	./scripts/import-gaia-db-from-nas.sh

lint: lint-backend lint-frontend

lint-backend:
	@cache_dir=$$(mktemp -d); trap 'rm -rf "$$cache_dir"' EXIT; \
		PYTHONPYCACHEPREFIX="$$cache_dir" $(QUALITY_PYTHON) -m compileall -q backend/app backend/tests modules/elaborazioni/worker
	$(QUALITY_PYTHON) scripts/check_changed_python_style.py --base-ref $${BASE_REF:-origin/main}

style-ratchet:
	$(QUALITY_PYTHON) scripts/check_changed_python_style.py --base-ref $${BASE_REF:-origin/main}

lint-backend-all:
	$(QUALITY_PYTHON) -m compileall -q backend/app backend/tests modules/elaborazioni/worker
	$(QUALITY_PYTHON) -m ruff check backend/app backend/tests backend/alembic/env.py modules/elaborazioni/worker scripts tools tests/code_quality

format-backend:
	$(QUALITY_PYTHON) -m ruff format backend/app backend/tests backend/alembic/env.py modules/elaborazioni/worker scripts tools tests/code_quality

lint-frontend:
	cd frontend && npm run lint

complexity-report:
	$(QUALITY_PYTHON) tools/code_quality/complexity.py report --json $${REPORT_JSON:-reports/code-quality/complexity-report.json} --markdown $${REPORT_MD:-reports/code-quality/complexity-report.md}

complexity-check:
	$(QUALITY_PYTHON) tools/code_quality/complexity.py check

complexity-changed:
	$(QUALITY_PYTHON) tools/code_quality/complexity.py changed --base-ref $${BASE_REF:-origin/main}

complexity-ratchet:
	$(QUALITY_PYTHON) tools/code_quality/complexity.py ratchet --base-ref $${BASE_REF:-origin/main}

complexity-baseline:
	$(QUALITY_PYTHON) tools/code_quality/complexity.py baseline

complexity-baseline-verify:
	$(QUALITY_PYTHON) tools/code_quality/complexity.py baseline-verify

complexity-ci-gate:
	QUALITY_PYTHON=$(QUALITY_PYTHON) scripts/complexity_ci_gate.sh

quality-test:
	$(QUALITY_PYTHON) -m pytest -q tests/code_quality

graphify-patch-openai-base-url:
	GRAPHIFY_BIN=$$(which graphify); PYTHON=$$(head -1 "$$GRAPHIFY_BIN" | tr -d '#!'); "$$PYTHON" scripts/patch_graphify_openai_base_url.py

.PHONY: graphify-patch-force-pruning
graphify-patch-force-pruning:
	GRAPHIFY_BIN=$$(which graphify); PYTHON=$$(head -1 "$$GRAPHIFY_BIN" | tr -d '#!'); "$$PYTHON" scripts/patch_graphify_force_pruning.py

graphify-refresh-core-code:
	$(MAKE) graphify-catasto-code
	$(MAKE) graphify-presenze-code
	$(MAKE) graphify-network-code
	$(MAKE) graphify-operazioni-code
	$(MAKE) graphify-organigramma-code
	$(MAKE) graphify-riordino-code
	$(MAKE) graphify-ruolo-code
	$(MAKE) graphify-utenze-code
	$(MAKE) graphify-wiki-code

graphify-refresh-core-docs:
	$(MAKE) graphify-catasto-docs
	$(MAKE) graphify-presenze-docs
	$(MAKE) graphify-network-docs
	$(MAKE) graphify-operazioni-docs
	$(MAKE) graphify-organigramma-docs
	$(MAKE) graphify-riordino-docs
	$(MAKE) graphify-ruolo-docs
	$(MAKE) graphify-utenze-docs
	$(MAKE) graphify-wiki-docs

graphify-refresh-core:
	$(MAKE) graphify-refresh-core-code
	$(MAKE) graphify-refresh-core-docs

graphify-catasto-code:
	cd backend/app/modules/catasto && $(GRAPHIFY_ENV) graphify update . $(GRAPHIFY_CODE_FLAGS)

graphify-catasto-docs:
	cd domain-docs/catasto && $(GRAPHIFY_ENV) graphify extract .

graphify-catasto-query:
	@if [ -z "$(Q)" ]; then echo "Uso: make graphify-catasto-query Q=\"domanda\""; exit 1; fi
	cd backend/app/modules/catasto && $(GRAPHIFY_ENV) graphify query "$(Q)"

graphify-presenze-code:
	cd backend/app/modules/presenze && $(GRAPHIFY_ENV) graphify update . $(GRAPHIFY_CODE_FLAGS)

graphify-presenze-docs:
	cd domain-docs/presenze && $(GRAPHIFY_ENV) GRAPHIFY_OPENAI_MODEL=$(GRAPHIFY_PRESENZE_DOC_MODEL) $(GRAPHIFY_PRESENZE_DOC_TIMEOUT) graphify extract . $(GRAPHIFY_PRESENZE_DOC_FLAGS)

graphify-presenze-query:
	@if [ -z "$(Q)" ]; then echo "Uso: make graphify-presenze-query Q=\"domanda\""; exit 1; fi
	cd backend/app/modules/presenze && $(GRAPHIFY_ENV) graphify query "$(Q)"

graphify-inaz-code:
	@echo "Alias legacy: uso graphify-presenze-code"
	@$(MAKE) graphify-presenze-code

graphify-inaz-docs:
	@echo "Alias legacy: uso graphify-presenze-docs"
	@$(MAKE) graphify-presenze-docs

graphify-inaz-query:
	@echo "Alias legacy: uso graphify-presenze-query"
	@$(MAKE) graphify-presenze-query Q="$(Q)"

graphify-network-code:
	cd backend/app/modules/network && $(GRAPHIFY_ENV) graphify update . $(GRAPHIFY_CODE_FLAGS)

graphify-network-docs:
	cd domain-docs/network && $(GRAPHIFY_ENV) graphify extract .

graphify-network-query:
	@if [ -z "$(Q)" ]; then echo "Uso: make graphify-network-query Q=\"domanda\""; exit 1; fi
	cd backend/app/modules/network && $(GRAPHIFY_ENV) graphify query "$(Q)"

graphify-operazioni-code:
	cd backend/app/modules/operazioni && $(GRAPHIFY_ENV) graphify update . $(GRAPHIFY_CODE_FLAGS)

graphify-elaborazioni-worker-code:
	cd modules/elaborazioni/worker && $(GRAPHIFY_ENV) graphify update . $(GRAPHIFY_CODE_FLAGS)

graphify-elaborazioni-worker-query:
	@if [ -z "$(Q)" ]; then echo "Uso: make graphify-elaborazioni-worker-query Q=\"domanda\""; exit 1; fi
	cd modules/elaborazioni/worker && $(GRAPHIFY_ENV) graphify query "$(Q)"

graphify-elaborazioni-docs:
	cd domain-docs/elaborazioni && $(GRAPHIFY_ENV) GRAPHIFY_OPENAI_MODEL=$(GRAPHIFY_ELABORAZIONI_DOC_MODEL) $(GRAPHIFY_ELABORAZIONI_DOC_TIMEOUT) graphify extract . $(GRAPHIFY_ELABORAZIONI_DOC_FLAGS)

graphify-elaborazioni-docs-query:
	@if [ -z "$(Q)" ]; then echo "Uso: make graphify-elaborazioni-docs-query Q=\"domanda\""; exit 1; fi
	cd domain-docs/elaborazioni && $(GRAPHIFY_ENV) graphify query "$(Q)"

graphify-operazioni-docs:
	cd domain-docs/operazioni && $(GRAPHIFY_ENV) graphify extract .

graphify-operazioni-query:
	@if [ -z "$(Q)" ]; then echo "Uso: make graphify-operazioni-query Q=\"domanda\""; exit 1; fi
	cd backend/app/modules/operazioni && $(GRAPHIFY_ENV) graphify query "$(Q)"

graphify-organigramma-code:
	cd backend/app/modules/organigramma && $(GRAPHIFY_ENV) graphify update . $(GRAPHIFY_CODE_FLAGS)

graphify-organigramma-docs:
	cd domain-docs/organigramma && $(GRAPHIFY_ENV) graphify extract .

graphify-organigramma-query:
	@if [ -z "$(Q)" ]; then echo "Uso: make graphify-organigramma-query Q=\"domanda\""; exit 1; fi
	cd backend/app/modules/organigramma && $(GRAPHIFY_ENV) graphify query "$(Q)"

graphify-riordino-code:
	cd backend/app/modules/riordino && $(GRAPHIFY_ENV) graphify update . $(GRAPHIFY_CODE_FLAGS)

graphify-riordino-docs:
	cd domain-docs/riordino && $(GRAPHIFY_ENV) graphify extract .

graphify-riordino-query:
	@if [ -z "$(Q)" ]; then echo "Uso: make graphify-riordino-query Q=\"domanda\""; exit 1; fi
	cd backend/app/modules/riordino && $(GRAPHIFY_ENV) graphify query "$(Q)"

graphify-ruolo-code:
	cd backend/app/modules/ruolo && $(GRAPHIFY_ENV) graphify update . $(GRAPHIFY_CODE_FLAGS)

graphify-ruolo-docs:
	cd domain-docs/ruolo && $(GRAPHIFY_ENV) graphify extract .

graphify-ruolo-query:
	@if [ -z "$(Q)" ]; then echo "Uso: make graphify-ruolo-query Q=\"domanda\""; exit 1; fi
	cd backend/app/modules/ruolo && $(GRAPHIFY_ENV) graphify query "$(Q)"

graphify-utenze-code:
	cd backend/app/modules/utenze && $(GRAPHIFY_ENV) graphify update . $(GRAPHIFY_CODE_FLAGS)

graphify-utenze-docs:
	cd domain-docs/utenze && $(GRAPHIFY_ENV) GRAPHIFY_OPENAI_MODEL=$(GRAPHIFY_UTENZE_DOC_MODEL) $(GRAPHIFY_UTENZE_DOC_TIMEOUT) graphify extract . $(GRAPHIFY_UTENZE_DOC_FLAGS)

graphify-utenze-query:
	@if [ -z "$(Q)" ]; then echo "Uso: make graphify-utenze-query Q=\"domanda\""; exit 1; fi
	cd backend/app/modules/utenze && $(GRAPHIFY_ENV) graphify query "$(Q)"

graphify-wiki-code:
	cd backend/app/modules/wiki && $(GRAPHIFY_ENV) graphify update . $(GRAPHIFY_CODE_FLAGS)

graphify-wiki-docs:
	cd domain-docs/wiki && $(GRAPHIFY_ENV) GRAPHIFY_OPENAI_MODEL=$(GRAPHIFY_WIKI_DOC_MODEL) $(GRAPHIFY_WIKI_DOC_TIMEOUT) graphify extract . $(GRAPHIFY_WIKI_DOC_FLAGS)

graphify-wiki-docs-debug:
	rm -f $(GRAPHIFY_WIKI_DOC_DEBUG_LOG)
	bash -lc 'cd domain-docs/wiki && $(GRAPHIFY_ENV) GRAPHIFY_OPENAI_MODEL=$(GRAPHIFY_WIKI_DOC_MODEL) PYTHONUNBUFFERED=1 $(GRAPHIFY_WIKI_DOC_DEBUG_TIMEOUT) stdbuf -oL -eL graphify extract . $(GRAPHIFY_WIKI_DOC_DEBUG_FLAGS) 2>&1 | tee $(GRAPHIFY_WIKI_DOC_DEBUG_LOG); test $${PIPESTATUS[0]} -eq 0'

graphify-wiki-query:
	@if [ -z "$(Q)" ]; then echo "Uso: make graphify-wiki-query Q=\"domanda\""; exit 1; fi
	cd backend/app/modules/wiki && $(GRAPHIFY_ENV) graphify query "$(Q)"

graphify-backend: graphify-patch-force-pruning
	cd backend/app && $(GRAPHIFY_ENV) graphify update . $(GRAPHIFY_CODE_FLAGS)

.PHONY: graphify-dotazioni-code graphify-dotazioni-docs graphify-dotazioni-query

graphify-dotazioni-code:
	cd backend/app/modules/dotazioni && $(GRAPHIFY_ENV) graphify update . $(GRAPHIFY_CODE_FLAGS)

graphify-dotazioni-docs:
	cd domain-docs/dotazioni && $(GRAPHIFY_ENV) GRAPHIFY_OPENAI_MODEL=$(GRAPHIFY_DOC_MODEL) timeout --foreground 420s graphify extract . --max-concurrency 1 --api-timeout 180

graphify-dotazioni-query:
	@if [ -z "$(Q)" ]; then echo "Uso: make graphify-dotazioni-query Q=\"domanda\""; exit 1; fi
	cd backend/app/modules/dotazioni && $(GRAPHIFY_ENV) graphify query "$(Q)"

graphify-backend-query:
	@if [ -z "$(Q)" ]; then echo "Uso: make graphify-backend-query Q=\"domanda\""; exit 1; fi
	cd backend/app && $(GRAPHIFY_ENV) graphify query "$(Q)"

graphify-frontend:
	cd frontend/src && $(GRAPHIFY_ENV) graphify update . $(GRAPHIFY_CODE_FLAGS)

graphify-frontend-query:
	@if [ -z "$(Q)" ]; then echo "Uso: make graphify-frontend-query Q=\"domanda\""; exit 1; fi
	cd frontend/src && $(GRAPHIFY_ENV) graphify query "$(Q)"

graphify-docs:
	cd domain-docs && $(GRAPHIFY_ENV) graphify extract .

graphify-docs-query:
	@if [ -z "$(Q)" ]; then echo "Uso: make graphify-docs-query Q=\"domanda\""; exit 1; fi
	cd domain-docs && $(GRAPHIFY_ENV) graphify query "$(Q)"

graphify-platform-docs:
	cd docs && $(GRAPHIFY_ENV) GRAPHIFY_OPENAI_MODEL=$(GRAPHIFY_PLATFORM_DOC_MODEL) graphify extract . $(GRAPHIFY_PLATFORM_DOC_FLAGS)

graphify-platform-docs-query:
	@if [ -z "$(Q)" ]; then echo "Uso: make graphify-platform-docs-query Q=\"domanda\""; exit 1; fi
	cd docs && $(GRAPHIFY_ENV) graphify query "$(Q)"

graphify-query:
	@if [ -z "$(Q)" ]; then echo "Uso: make graphify-query Q=\"domanda\""; exit 1; fi
	$(GRAPHIFY_ENV) graphify query "$(Q)"

GO_BIN ?= go
GOFMT_BIN ?= $(if $(findstring /,$(GO_BIN)),$(dir $(GO_BIN))gofmt,gofmt)
MCP_CA_CERT ?=
MCP_CA_BUNDLE ?= runtime-data/mcps/client-ca

.PHONY: mcp-ca-bundle test-mcp-tls lint-mcp-tls
.PHONY: test-mcp-gateway
test-mcp-gateway:
	$(QUALITY_PYTHON) -m pytest -q tests/infrastructure/test_mcp_tls_gateway.py

mcp-ca-bundle:
	GO_BIN="$(GO_BIN)" bash scripts/tls/build-client-bundle.sh "$(MCP_CA_CERT)" "$(MCP_CA_BUNDLE)"

test-mcp-tls:
	cd installer/windows && GOTOOLCHAIN=local GOPROXY=off "$(GO_BIN)" test -coverprofile=/tmp/gaia-mcp-ca-core.cover core.go core_test.go
	"$(GO_BIN)" tool cover -func=/tmp/gaia-mcp-ca-core.cover > /tmp/gaia-mcp-ca-core-coverage.txt
	cat /tmp/gaia-mcp-ca-core-coverage.txt
	awk '/^total:/ { found=1; if ($$NF != "100.0%") exit 1 } END { if (!found) exit 1 }' /tmp/gaia-mcp-ca-core-coverage.txt
	bash scripts/tls/test-client-installers.sh

lint-mcp-tls:
	unformatted="$$("$(GOFMT_BIN)" -l installer/windows/*.go)" && test -z "$$unformatted"
	GOTOOLCHAIN=local GOPROXY=off "$(GO_BIN)" vet installer/windows/core.go installer/windows/core_test.go
	for script in scripts/tls/*.sh; do bash -n "$$script" || exit; done
