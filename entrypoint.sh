#!/bin/bash
set -e

export PYTHONPATH=/app

echo "Выполняем миграции Alembic..."
alembic upgrade head

echo "Наполняем базу данных начальными данными..."
python database/fetch_vacancies.py

echo "Запускаем Telegram-бота..."
python -m bot.main
