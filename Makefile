# EcoNexo — comandos de desarrollo.
# Requiere: Docker + Docker Compose v2.

SHELL := /bin/bash

.PHONY: help up down build logs seed demo sim test ps clean

help:
	@echo "EcoNexo — targets:"
	@echo "  make up      Levanta todo el ecosistema (docker compose up -d)"
	@echo "  make build   Rebuild de todas las imagenes"
	@echo "  make seed    Carga datos semilla (3 orgs, nodos, 30 dias de historial)"
	@echo "  make demo    Dispara la historia end-to-end en vivo"
	@echo "  make sim     Arranca el simulador de nodos ESP32 (perfil sim)"
	@echo "  make logs    Sigue los logs de todos los servicios"
	@echo "  make test    Corre los tests (correlacion espacial + motor de reglas)"
	@echo "  make down    Detiene el ecosistema"
	@echo "  make clean   Detiene y borra volumenes (datos!)"

up:
	docker compose up -d --build
	@echo "Esperando a la API..."
	@echo "Dashboard:  http://localhost:3000"
	@echo "API/Swagger: http://localhost:8000/docs"
	@echo "MinIO:      http://localhost:9090"

build:
	docker compose build

seed:
	docker compose run --rm api python -m app.seed

demo:
	docker compose run --rm api python -m app.demo

sim:
	docker compose --profile sim up -d --build simulator

logs:
	docker compose logs -f

ps:
	docker compose ps

test:
	docker compose run --rm api pytest -q

down:
	docker compose down

clean:
	docker compose down -v
