# EcoNexo — comandos de desarrollo y validación.
SHELL := /bin/bash

.PHONY: help up down build logs seed demo sim test test-api test-web test-mobile validate ps clean

help:
	@echo "EcoNexo — targets:"
	@echo "  make up         Levanta el ecosistema local"
	@echo "  make build      Reconstruye las imágenes"
	@echo "  make seed       Carga datos semilla"
	@echo "  make demo       Ejecuta la historia end-to-end"
	@echo "  make sim        Inicia el simulador ESP32"
	@echo "  make validate   Tests API + chequeos TypeScript web/móvil"
	@echo "  make logs       Sigue logs"
	@echo "  make down       Detiene servicios"
	@echo "  make clean      Detiene y elimina volúmenes"

up:
	docker compose up -d --build
	@echo "App:         http://localhost:3000"
	@echo "API/Swagger: http://localhost:8000/docs"
	@echo "MinIO:       http://localhost:9090"

build:
	docker compose build

seed:
	docker compose run --rm api python -m app.seed

demo:
	docker compose run --rm api python -m app.demo

sim:
	docker compose --profile sim up -d --build simulator

test: validate

test-api:
	docker compose run --rm api pytest -q

test-web:
	docker compose run --rm --no-deps web npm run typecheck

test-mobile:
	cd apps/mobile && npm run typecheck

validate: test-api test-web test-mobile

logs:
	docker compose logs -f

ps:
	docker compose ps

down:
	docker compose down

clean:
	docker compose down -v
