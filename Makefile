.PHONY: help build up down logs clean restart

help: ## Показать справку
	@echo "Доступные команды:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

build: ## Собрать Docker образ
	docker-compose build

up: ## Запустить контейнер
	docker-compose up -d

down: ## Остановить контейнер
	docker-compose down

logs: ## Показать логи контейнера
	docker-compose logs -f gorzdrav-bot

clean: ## Очистить контейнер и образ
	docker-compose down --rmi all --volumes --remove-orphans

restart: ## Перезапустить контейнер
	docker-compose restart

shell: ## Войти в контейнер
	docker-compose exec gorzdrav-bot /bin/bash

status: ## Показать статус контейнеров
	docker-compose ps

# Создание необходимых директорий
setup:
	mkdir -p logs
	chmod 755 logs

# Первый запуск
first-run: setup build up
	@echo "Контейнер запущен! Проверьте логи: make logs"
