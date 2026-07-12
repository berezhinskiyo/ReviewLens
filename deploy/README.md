# Деплой ReviewLens — два окружения на общем сервере

Сервер: `root@5.35.103.48` (msk-1-vm-7ibp). На нём живут ЧЕТЫРЕ стека
(cvtailor test/prod + reviewlens test/prod) за **единым edge-Caddy**, который владеет
80/443 и терминирует TLS (Let's Encrypt). Каждый стек отдаёт nginx на свой loopback-порт.

| Окружение | Ветка  | Домен                          | Каталог               | Loopback-порт |
|-----------|--------|--------------------------------|-----------------------|---------------|
| test      | `test` | `reviewlens.test.vniknu.ru`    | `/opt/reviewlens-test`| `127.0.0.1:28081` |
| prod      | `prod` | `reviewlens.vniknu.ru`         | `/opt/reviewlens-prod`| `127.0.0.1:18081` |

Распределение портов на сервере: cvtailor prod `18080` / test `28080`,
reviewlens prod `18081` / test `28081`.

## Каскад релизов (`.github/workflows/deploy.yml`)

```
push main  → force-push в test  (→ деплой TEST)
push test  → деплой TEST         → (при DEPLOY_PROD_ENABLED=true) force-push в prod
push prod  → деплой PROD          (при DEPLOY_PROD_ENABLED=true)
```

- Секрет репозитория **`SSH_PRIVATE_KEY`** — приватный ключ для входа на сервер.
- Repo-переменная **`DEPLOY_PROD_ENABLED`**: пока не `true`, любой push катит **только TEST**;
  прод включается осознанно. (Settings → Secrets and variables → Actions → Variables.)
- **Миграции** alembic гоняются шагом деплоя (`docker compose run --rm backend alembic upgrade head`),
  т.к. в образе backend их нет в CMD.

## Бутстрап (всё через GitHub — ручной SSH не нужен)

Секреты живут в GitHub, деплой сам пишет `.env` на сервер. Полный список констант —
в **`GITHUB_SECRETS.md`**. Кратко:

### 1. Заполнить секреты GitHub (оба репо)
- Repo secret `SSH_PRIVATE_KEY`, repo secret `SHARED_POSTGRES_DOTENV` (только ReviewLens).
- Repo variable `DEPLOY_PROD_ENABLED` — пока не задавать.
- Environments `test` и `prod`, в каждом секрет `DOTENV` с полным .env окружения.

### 2. Поднять общую инфраструктуру (по кнопке)
ReviewLens → **Actions → Deploy → Run workflow** с галочкой **bootstrap**. Job
`bootstrap-infra`:
- остановит старые `/opt/cv-tailor` и `/opt/reviewlens` (освободит 80/443);
- поднимет **общий PostgreSQL** (`/opt/shared-postgres`, сеть `shared`, 4 базы+роли из
  `SHARED_POSTGRES_DOTENV`);
- поднимет **edge-Caddy** (`/opt/edge`, 80/443 + авто-TLS на 4 домена).

### 3. OAuth
Redirect URI всех доменов добавить в приложениях Яндекс/VK.

### 4. Деплой
Пуш в `main` (или `test`) каждого репо → раскатит **TEST** (prod за флагом
`DEPLOY_PROD_ENABLED`). Каталоги `/opt/*-{test,prod}` создаются автоматически.

> Файлы `deploy/env.*.example` и `deploy/shared-postgres/env.example` оставлены как
> справочные шаблоны значений — на сервер их класть НЕ нужно, всё идёт из GitHub.

## Скраперы
По умолчанию worker собирается из обычного `backend/Dockerfile` — работают **WB и
Мегамаркет** (без браузера). Для Ozon / Яндекс.Маркет / Avito нужен образ с Playwright
(`backend/Dockerfile.playwright`) и резидентный РФ-прокси `SCRAPER_PROXY`. Чтобы включить,
добавь оверрайд `docker-compose.scrapers.yml` в цепочку `COMPOSE_FILE` окружения.

## Изоляция
Разные `COMPOSE_PROJECT_NAME` → отдельные сети и контейнеры. Данные — в ОБЩЕМ
PostgreSQL, но у каждого окружения своя база и роль (test не видит prod). Redis
у каждого стека свой (общий только PG).
