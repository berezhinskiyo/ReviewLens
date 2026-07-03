# ReviewLens

AI-анализ отзывов конкурентов на маркетплейсах (Wildberries). Селлер вставляет
ссылку на карточку конкурента — через 2–5 минут получает структурированный
отчёт: на что жалуются покупатели, что хвалят, и какие идеи внедрить.

## Стек

- **Backend:** Python 3.11, FastAPI, SQLAlchemy 2.0 (async) + asyncpg, Alembic,
  Redis + RQ, httpx, **OpenAI SDK** (ChatGPT), python-jose (JWT) + passlib
  (bcrypt), ЮKassa.
- **Frontend:** Vite + React 18 + react-router-dom (SPA), плоский CSS-дизайн-система.
- **Инфраструктура:** PostgreSQL 15, Redis 7, Docker Compose, Caddy (prod, HTTPS).

## Авторизация

Заимствована из проекта cv-tailor и адаптирована под async-стек:

- регистрация по **email + пароль** с подтверждением **6-значным кодом** на почту;
- вход по email/паролю;
- **OAuth** через Яндекс и VK (redirect → `/auth/oauth/callback`);
- **JWT** access (короткий) + refresh-токены (хранятся в БД только как sha256-хеш,
  ротация при обновлении);
- защита капчей Яндекс **SmartCaptcha** (опционально), device-fingerprint,
  фиксация согласия на обработку ПДн (152-ФЗ).

Фронтенд: `AuthContext` + `ProtectedRoute` + `api/client.ts` с авто-refresh.

## LLM-пайплайн (OpenAI)

1. **Extract** (`gpt-4o-mini`): отзывы делятся на чанки по 30, из каждого
   извлекаются claims_negative / claims_positive / тональность.
2. **Cluster** (`gpt-4o-mini`): claims кластеризуются в темы с частотой и примерами.
3. **Synthesize** (`gpt-4o-mini`): итоговый `result` JSON по схеме
   `app/schemas/result.py`.

Используется Chat Completions с `response_format=json_object`. Модели
параметризуются через `.env` (`OPENAI_MODEL_*`). Фактическая стоимость анализа
фиксируется в `analyses.llm_cost_kopecks`. Все промпты — в `app/llm/prompts.py`.

## Запуск локально

```bash
# 1. Конфиг backend (вставьте свой OPENAI_API_KEY)
cp backend/.env.example backend/.env

# 2. Конфиг frontend (опционально)
cp frontend/.env.example frontend/.env.local

# 3. Поднять стек
docker-compose up -d --build

# 4. Применить миграции
docker-compose exec backend alembic upgrade head

# 5. (опционально) тестовый пользователь + токен
docker-compose exec backend python -m app.scripts.create_test_user
```

- Frontend: http://localhost:5173
- Backend API + Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/api/health

В dev Vite проксирует `/api` → backend (см. `frontend/vite.config.ts`).

## Тесты

```bash
cd backend
pip install -e ".[dev]"
pytest                                 # юнит-тесты (без сети)
RUN_LIVE_SCRAPER=1 pytest -k live       # живой парсинг WB
RUN_LLM_E2E=1 pytest -k prompts_e2e -s  # e2e пайплайн на фикстуре (тратит токены OpenAI)
```

## Маркетплейсы

| Площадка | Метод | Примечание |
|---|---|---|
| Wildberries | httpx (basket-CDN + feedbacks) | стабильно |
| Мегамаркет | httpx (mobile JSON-API) | нужен чистый РФ-IP сервера |
| Ozon | Playwright (перехват composer-api) | нужен headless-воркер; в проде — прокси |
| Яндекс.Маркет | Playwright | SmartCaptcha — нужны резидентные прокси |
| Avito | Playwright | отзывы о продавце; сильный анти-бот |

Скрапер выбирается по домену (`app/scrapers/registry.py`). В проде по умолчанию
включён **только Wildberries** (`ENABLED_MARKETPLACES=wb`) — он не требует браузера и
работает стабильно. Остальные площадки есть в коде, но отключены: их анти-бот
(Ozon/Яндекс — SmartCaptcha/Qrator, Мегамаркет/Avito — блок по IP) не пробивается
ни резидентными прокси, ни базовыми scraping-API-триалами (проверено). Для их
включения нужен платный анти-бот-источник (Web Unlocker с РФ-гео) — тогда
`ENABLED_MARKETPLACES=wb,ozon,...` и воркер с браузером:

```bash
docker compose -f docker-compose.yml -f docker-compose.scrapers.yml up -d --build worker
```

## Деплой (прод)

Единый домен: Caddy маршрутизирует `/api/*` → backend, остальное → статика фронта
(nginx). OAuth redirect и ссылка обратно во фронт работают на одном домене.

```bash
cp backend/.env.example backend/.env   # боевые ключи; FRONTEND_URL=BACKEND_URL=https://домен
# отредактировать Caddyfile под свой домен
docker-compose -f docker-compose.prod.yml up -d --build
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

### Sentry

Логи в JSON через loguru (`app/core/logging.py`). Для Sentry добавьте
`sentry-sdk` и инициализацию в `app/main.py` (следующий шаг, см. BACKLOG.md).

## Что НЕ входит в MVP

См. `BACKLOG.md`: Ozon, мониторинг, экспорт в Excel/PDF, админка экономики и др.
