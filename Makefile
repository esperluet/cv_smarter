DC := docker compose

.PHONY: build up down logs ps restart clean backend-shell frontend-shell db-shell migrate test

build:
	$(DC) build

up:
	$(DC) up -d --build

down:
	$(DC) down

logs:
	$(DC) logs -f

ps:
	$(DC) ps

restart: down up

backend-shell:
	$(DC) exec backend sh

frontend-shell:
	$(DC) exec frontend sh

db-shell:
	$(DC) exec postgres psql -U cv_optimizer -d cv_optimizer

migrate:
	$(DC) run --rm backend alembic upgrade head

test:
	$(DC) run --rm backend pytest -q

clean:
	$(DC) down --volumes --remove-orphans
