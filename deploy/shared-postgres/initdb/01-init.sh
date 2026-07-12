#!/bin/bash
# Создаёт по одной базе+роли на каждое окружение. Выполняется ТОЛЬКО при первом
# старте контейнера (пустой volume). Пароли ролей берутся из env контейнера.
# Чтобы добавить БД позже (на уже инициализированном volume) — выполнить эти же
# CREATE вручную: docker exec -it shared-postgres psql -U postgres
set -euo pipefail

create_env_db() {
  local db="$1" user="$2" pass="$3"
  if [ -z "$pass" ]; then
    echo "WARN: пароль для роли $user пуст — пропускаю создание $db"
    return 0
  fi
  psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" <<-EOSQL
    CREATE ROLE "$user" LOGIN PASSWORD '$pass';
    CREATE DATABASE "$db" OWNER "$user";
EOSQL
  echo "created database $db (owner $user)"
}

create_env_db cvtailor_prod   cvtailor_prod   "${CVTAILOR_PROD_DB_PASSWORD:-}"
create_env_db cvtailor_test   cvtailor_test   "${CVTAILOR_TEST_DB_PASSWORD:-}"
create_env_db reviewlens_prod reviewlens_prod "${REVIEWLENS_PROD_DB_PASSWORD:-}"
create_env_db reviewlens_test reviewlens_test "${REVIEWLENS_TEST_DB_PASSWORD:-}"
