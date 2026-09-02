COMPOSE = docker compose
GRAPHIFY_ENV = if [ -f /home/cbo/CursorProjects/GAIA/.env.graphify ]; then set -a; . /home/cbo/CursorProjects/GAIA/.env.graphify; set +a; fi;
GRAPHIFY_CODE_FLAGS ?=
GRAPHIFY_WIKI_DOC_MODEL = gpt-5.4-mini
GRAPHIFY_WIKI_DOC_FLAGS = --max-concurrency 1 --api-timeout 60
GRAPHIFY_WIKI_DOC_TIMEOUT = timeout --foreground 180s
GRAPHIFY_WIKI_DOC_DEBUG_FLAGS = --max-concurrency 1 --api-timeout 30
GRAPHIFY_WIKI_DOC_DEBUG_TIMEOUT = timeout --foreground 90s
GRAPHIFY_WIKI_DOC_DEBUG_LOG = /tmp/graphify-wiki-docs-debug.log
GRAPHIFY_PRESENZE_DOC_MODEL = gpt-5.4-mini
GRAPHIFY_PRESENZE_DOC_FLAGS = --max-concurrency 1 --api-timeout 60
GRAPHIFY_PRESENZE_DOC_TIMEOUT = timeout --foreground 180s
GRAPHIFY_UTENZE_DOC_MODEL = gpt-5.4-mini
GRAPHIFY_UTENZE_DOC_FLAGS = --max-concurrency 1 --api-timeout 60
GRAPHIFY_UTENZE_DOC_TIMEOUT = timeout --foreground 180s
GRAPHIFY_PLATFORM_DOC_MODEL = gpt-5.4-mini
GRAPHIFY_PLATFORM_DOC_FLAGS = --max-concurrency 1 --api-timeout 60
QUALITY_PYTHON ?= python3
WORKER_PYTHON ?= backend/.venv/bin/python
WORKER_COVERAGE_JSON ?= backend/coverage-worker.json
WORKER_COVERAGE_XML ?= backend/coverage-worker.xml

.PHONY: test-ruolo-postgres test-presenze-postgres

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
	$(QUALITY_PYTHON) -m compileall -q backend/app backend/tests modules/elaborazioni/worker
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

graphify-backend:
	cd backend/app && $(GRAPHIFY_ENV) graphify update . $(GRAPHIFY_CODE_FLAGS)

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
