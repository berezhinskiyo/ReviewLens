# Секреты и переменные GitHub — ReviewLens

Все секреты — в GitHub (Settings → Secrets and variables → Actions). Деплой сам пишет
`.env` на сервер из секрета `DOTENV` соответствующего Environment. Общий PostgreSQL и
edge поднимаются ручным запуском workflow (Run workflow → bootstrap) из секрета
`SHARED_POSTGRES_DOTENV`. Вручную на сервере ничего держать не нужно.

## 1. Repository secrets
| Имя | Значение |
|-----|----------|
| `SSH_PRIVATE_KEY` | приватный SSH-ключ для `root@109.73.197.92` |
| `SHARED_POSTGRES_DOTENV` | полный .env общего PostgreSQL (см. блок ниже) |

## 2. Repository variables
| Имя | Значение |
|-----|----------|
| `DEPLOY_PROD_ENABLED` | не задавать (или `false`); `true` — включить деплой prod |

## 3. Секрет `SHARED_POSTGRES_DOTENV` (общий PostgreSQL, один на весь сервер)
Пароли ролей ДОЛЖНЫ совпадать с `DB_PASSWORD`/`POSTGRES_PASSWORD` в .env окружений.
```dotenv
POSTGRES_SUPERUSER_PASSWORD=<пароль суперюзера postgres>
CVTAILOR_PROD_DB_PASSWORD=<= DB_PASSWORD в cvtailor prod DOTENV>
CVTAILOR_TEST_DB_PASSWORD=<= DB_PASSWORD в cvtailor test DOTENV>
REVIEWLENS_PROD_DB_PASSWORD=<= POSTGRES_PASSWORD в reviewlens prod DOTENV>
REVIEWLENS_TEST_DB_PASSWORD=<= POSTGRES_PASSWORD в reviewlens test DOTENV>
```

## 4. Environments → секрет `DOTENV`
Создать Environment **`test`** и **`prod`**, в каждом секрет **`DOTENV`** с полным .env.

### Environment `test` → секрет `DOTENV`
```dotenv
COMPOSE_FILE=docker-compose.deploy.yml
COMPOSE_PROJECT_NAME=reviewlens-test
WEB_PORT=28081
# БД в общем PostgreSQL. POSTGRES_PASSWORD = REVIEWLENS_TEST_DB_PASSWORD в shared-postgres
POSTGRES_USER=reviewlens_test
POSTGRES_PASSWORD=<пароль БД reviewlens_test>
POSTGRES_DB=reviewlens_test
JWT_SECRET_KEY=<секрет JWT test>
OPENAI_API_KEY=<ключ polza.ai>
OPENAI_BASE_URL=https://polza.ai/api/v1
OPENAI_MODEL_EXTRACT=google/gemini-2.5-flash-lite
OPENAI_MODEL_CLUSTER=google/gemini-2.5-flash-lite
OPENAI_MODEL_SYNTH=deepseek/deepseek-v3.2
FRONTEND_URL=https://reviewlens.test.vniknu.ru
BACKEND_URL=https://reviewlens.test.vniknu.ru
CONSENT_VERSION=2026-06-29
BOOTSTRAP_ADMIN_EMAIL=<email админа>
SMARTCAPTCHA_SERVER_KEY=<...>
YANDEX_CLIENT_ID=<...>
YANDEX_CLIENT_SECRET=<...>
VK_CLIENT_ID=<...>
VK_CLIENT_SECRET=<...>
EMAIL_HTTP_ENDPOINT=https://postbox.cloud.yandex.net
EMAIL_HTTP_KEY_ID=
EMAIL_HTTP_SECRET=
SMTP_FROM=noreply@reviewlens.ru
# Т-Банк: на test — ДЕМО-терминал
TINKOFF_TERMINAL_KEY=1783498090224DEMO
TINKOFF_PASSWORD=<демо-пароль Т-Банка>
TINKOFF_API_URL=https://securepay.tinkoff.ru/v2/
TINKOFF_TAXATION=usn_income
TINKOFF_VAT=none
ENV=production
ENABLED_MARKETPLACES=wb
SCRAPER_PROXY=
MAX_REVIEWS_PER_ANALYSIS=500
ANALYSIS_COST_BUDGET_KOPECKS=1500
```

### Environment `prod` → секрет `DOTENV`
Отличия: имя/порт/база/URL и БОЕВЫЕ креды Т-Банка.
```dotenv
COMPOSE_FILE=docker-compose.deploy.yml
COMPOSE_PROJECT_NAME=reviewlens-prod
WEB_PORT=18081
POSTGRES_USER=reviewlens_prod
POSTGRES_PASSWORD=<пароль БД reviewlens_prod>
POSTGRES_DB=reviewlens_prod
JWT_SECRET_KEY=<секрет JWT prod>
OPENAI_API_KEY=<ключ polza.ai>
OPENAI_BASE_URL=https://polza.ai/api/v1
OPENAI_MODEL_EXTRACT=google/gemini-2.5-flash-lite
OPENAI_MODEL_CLUSTER=google/gemini-2.5-flash-lite
OPENAI_MODEL_SYNTH=deepseek/deepseek-v3.2
FRONTEND_URL=https://reviewlens.vniknu.ru
BACKEND_URL=https://reviewlens.vniknu.ru
CONSENT_VERSION=2026-06-29
BOOTSTRAP_ADMIN_EMAIL=<email админа>
SMARTCAPTCHA_SERVER_KEY=<...>
YANDEX_CLIENT_ID=<...>
YANDEX_CLIENT_SECRET=<...>
VK_CLIENT_ID=<...>
VK_CLIENT_SECRET=<...>
EMAIL_HTTP_ENDPOINT=https://postbox.cloud.yandex.net
EMAIL_HTTP_KEY_ID=
EMAIL_HTTP_SECRET=
SMTP_FROM=noreply@reviewlens.ru
# Т-Банк: БОЕВЫЕ креды
TINKOFF_TERMINAL_KEY=<боевой terminal key>
TINKOFF_PASSWORD=<боевой пароль>
TINKOFF_API_URL=https://securepay.tinkoff.ru/v2/
TINKOFF_TAXATION=usn_income
TINKOFF_VAT=none
ENV=production
ENABLED_MARKETPLACES=wb
SCRAPER_PROXY=<резидентный РФ-прокси для Ozon/Яндекс/Avito, иначе только WB/Мегамаркет>
MAX_REVIEWS_PER_ANALYSIS=500
ANALYSIS_COST_BUDGET_KOPECKS=1500
```

## Порядок первого запуска
1. Заполнить секреты выше (оба репо).
2. ReviewLens → Actions → Deploy → **Run workflow** с галочкой **bootstrap** — поднимет
   общий PostgreSQL + edge, остановит старые стеки.
3. Пуш в `main` (или в `test`) каждого репо → раскатит **TEST** (prod за флагом).
4. Обкатать test → выставить `DEPLOY_PROD_ENABLED=true` → пуш раскатит PROD.
