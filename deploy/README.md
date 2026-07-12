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

## Разовый бутстрап сервера

### 1. Единый edge-Caddy (один раз на весь сервер)
Файлы: `deploy/edge/docker-compose.yml` + `deploy/edge/Caddyfile` (4 домена).
```bash
mkdir -p /opt/edge
cp deploy/edge/docker-compose.yml deploy/edge/Caddyfile /opt/edge/
cd /opt/edge && docker compose up -d
```
Если на сервере УЖЕ есть общий Caddy — не поднимай этот стек, а добавь блоки из
`deploy/edge/Caddyfile` в существующий Caddyfile и сделай `caddy reload`.

> Внимание: пока edge (или существующий общий прокси) не владеет 80/443, старые
> `/opt/reviewlens` и `/opt/cv-tailor` со СВОИМ Caddy надо остановить (`docker compose down`),
> иначе конфликт портов. Данные не нужны (свежий старт) — старые каталоги можно удалить.

### 2. `.env` окружения (в git нет, деплой не трогает)
```bash
mkdir -p /opt/reviewlens-test /opt/reviewlens-prod
nano /opt/reviewlens-test/.env    # по deploy/env.test.example: WEB_PORT=28081, домен test, ДЕМО-креды Т-Банка
nano /opt/reviewlens-prod/.env    # по deploy/env.prod.example: WEB_PORT=18081, домен prod, БОЕВЫЕ креды Т-Банка
```
Обязательно разные `POSTGRES_PASSWORD` и `JWT_SECRET_KEY` для test и prod.

### 3. GitHub
- Секрет `SSH_PRIVATE_KEY` — на месте.
- `DEPLOY_PROD_ENABLED` не выставлять, пока не обкатан test.

### 4. OAuth
Redirect URI обоих доменов добавить в приложениях Яндекс/VK.

## Скраперы
По умолчанию worker собирается из обычного `backend/Dockerfile` — работают **WB и
Мегамаркет** (без браузера). Для Ozon / Яндекс.Маркет / Avito нужен образ с Playwright
(`backend/Dockerfile.playwright`) и резидентный РФ-прокси `SCRAPER_PROXY`. Чтобы включить,
добавь оверрайд `docker-compose.scrapers.yml` в цепочку `COMPOSE_FILE` окружения.

## Изоляция
Разные `COMPOSE_PROJECT_NAME` → отдельные volume (`pgdata`), сети и контейнеры;
данные test и prod не пересекаются.
