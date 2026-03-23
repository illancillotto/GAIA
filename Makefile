COMPOSE = docker compose

.PHONY: up down logs rebuild backend-shell frontend-shell migrate bootstrap-admin bootstrap-domain live-sync scheduled-live-sync

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
	$(COMPOSE) exec backend python scripts/bootstrap_admin.py

bootstrap-domain:
	$(COMPOSE) exec backend python scripts/bootstrap_domain.py

live-sync:
	$(COMPOSE) exec backend python scripts/live_sync.py

scheduled-live-sync:
	$(COMPOSE) exec backend python scripts/scheduled_live_sync.py
