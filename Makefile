COMPOSE = docker compose

.PHONY: up down logs rebuild backend-shell frontend-shell migrate bootstrap-admin bootstrap-domain bootstrap-sections purge-seed live-sync scheduled-live-sync local-gateway-up local-gateway-down wiki-index wiki-reindex wiki-proxy test test-wiki coverage-wiki smoke-network-vpn-bypass

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

wiki-proxy:
	nohup python3 scripts/codex-lb-proxy.py > /tmp/codex-lb-proxy.log 2>&1 &

wiki-index:
	$(COMPOSE) exec backend python -m app.modules.wiki.services.indexer

wiki-reindex:
	$(COMPOSE) exec backend python -c "from app.core.database import SessionLocal; from app.modules.wiki.services.indexer import index_documents; db=SessionLocal(); index_documents(db, force=True); db.close(); print('Reindex completato')"

test:
	$(COMPOSE) exec backend python -m pytest

test-wiki:
	$(COMPOSE) exec backend python -m pytest tests/test_wiki_indexer.py tests/test_wiki_rag.py tests/test_wiki_requests_api.py tests/test_wiki_articles_api.py tests/test_wiki_chat_api.py -v

coverage-wiki:
	$(COMPOSE) exec backend python -m pytest tests/test_wiki_indexer.py tests/test_wiki_rag.py tests/test_wiki_requests_api.py tests/test_wiki_articles_api.py tests/test_wiki_chat_api.py --cov=app/modules/wiki --cov-report=term-missing --cov-report=html:htmlcov/wiki

smoke-network-vpn-bypass:
	./scripts/smoke-network-vpn-bypass.sh
