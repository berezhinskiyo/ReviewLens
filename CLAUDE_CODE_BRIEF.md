# ТЗ для Claude Code: ReviewLens — AI-анализ отзывов конкурентов на маркетплейсах

> Это мастер-задание для пошаговой разработки MVP. Идти строго по фазам в конце документа. После каждой фазы — запуск, проверка, коммит. Не переходить к следующей фазе, пока предыдущая не работает.

---

## 1. Контекст продукта

**Что делаем:** веб-сервис по подписке. Селлер маркетплейса вставляет URL карточки конкурента на Wildberries или Ozon, через 2–5 минут получает структурированный отчёт по отзывам: на что жалуются покупатели, что хвалят, какие идеи для своего товара/инфографики/описания.

**Аудитория:** малые и средние селлеры WB/Ozon с оборотом 200 тыс. — 3 млн ₽/мес. Не разработчики, не аналитики. UI должен быть максимально простым.

**Бизнес-модель:** freemium. 1 бесплатный анализ при регистрации, далее подписка 990 ₽/мес (10 анализов) или 2990 ₽/мес (безлимит).

**Главные принципы:**
- Один экран — одна задача. Никаких комбайнов.
- Отчёт должен быть понятен селлеру без аналитической подготовки.
- Скорость важнее красоты: 5 минут на отчёт — потолок.
- Стоимость одного анализа в LLM-токенах должна быть ≤ 15 ₽, чтобы экономика сходилась.

---

## 2. Технологический стек

### Backend
- **Python 3.11+**
- **FastAPI** + **Uvicorn** — основной HTTP-сервер
- **SQLAlchemy 2.0** (async) + **asyncpg** — ORM
- **Alembic** — миграции
- **Pydantic v2** — валидация
- **Redis** + **RQ** — очередь фоновых задач
- **httpx** (async) — HTTP-клиент для парсинга
- **anthropic** SDK — вызовы Claude
- **python-jose** + **passlib** — JWT
- **yookassa** SDK — платежи
- **pytest** + **pytest-asyncio** — тесты

### Frontend
- **Next.js 15** (App Router) + **TypeScript**
- **Tailwind CSS** + **shadcn/ui** — UI
- **TanStack Query** — серверные данные
- **react-hook-form** + **zod** — формы

### Инфраструктура
- **PostgreSQL 15+**
- **Redis 7+**
- **Docker** + **docker-compose** для локальной разработки
- Деплой: Selectel/Timeweb Cloud, single VPS, через docker-compose

---

## 3. Структура проекта

Монорепозиторий:

```
/reviewlens
├── backend/
│   ├── app/
│   │   ├── api/              # FastAPI роуты
│   │   │   ├── deps.py       # зависимости (auth, db)
│   │   │   ├── auth.py
│   │   │   ├── analyses.py
│   │   │   ├── payments.py
│   │   │   └── users.py
│   │   ├── core/
│   │   │   ├── config.py     # Settings через pydantic-settings
│   │   │   ├── security.py   # JWT, проверка TG-подписи
│   │   │   └── logging.py
│   │   ├── db/
│   │   │   ├── base.py       # Base, session
│   │   │   ├── models.py     # SQLAlchemy модели
│   │   │   └── session.py
│   │   ├── schemas/          # Pydantic-схемы
│   │   ├── services/         # Бизнес-логика
│   │   │   ├── analysis.py
│   │   │   ├── subscription.py
│   │   │   └── payment.py
│   │   ├── workers/
│   │   │   ├── tasks.py      # RQ-задачи
│   │   │   └── worker.py     # entrypoint
│   │   ├── scrapers/
│   │   │   ├── base.py
│   │   │   ├── wildberries.py
│   │   │   └── ozon.py
│   │   ├── llm/
│   │   │   ├── client.py     # Anthropic клиент
│   │   │   ├── prompts.py    # все промпты в одном месте
│   │   │   └── pipeline.py   # оркестрация анализа
│   │   └── main.py
│   ├── alembic/
│   ├── tests/
│   ├── pyproject.toml
│   ├── Dockerfile
│   └── .env.example
├── frontend/
│   ├── app/
│   │   ├── (marketing)/      # лендинг
│   │   ├── (app)/            # приватная зона
│   │   │   ├── dashboard/
│   │   │   ├── analyses/
│   │   │   │   └── [id]/
│   │   │   ├── billing/
│   │   │   └── layout.tsx
│   │   ├── login/
│   │   └── layout.tsx
│   ├── components/
│   │   ├── ui/               # shadcn компоненты
│   │   ├── analysis/
│   │   └── auth/
│   ├── lib/
│   │   ├── api.ts            # клиент API
│   │   └── auth.ts
│   ├── package.json
│   └── Dockerfile
├── docker-compose.yml
├── docker-compose.prod.yml
├── README.md
└── .gitignore
```

---

## 4. Схема базы данных

```sql
-- Пользователи
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    telegram_id BIGINT UNIQUE NOT NULL,
    telegram_username VARCHAR(64),
    first_name VARCHAR(128),
    photo_url TEXT,
    email VARCHAR(255),                -- опционально, для уведомлений
    plan VARCHAR(32) NOT NULL DEFAULT 'free',  -- free / starter / pro
    subscription_until TIMESTAMPTZ,
    analyses_used_this_period INT NOT NULL DEFAULT 0,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Карточки товаров (кэш парсинга)
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    marketplace VARCHAR(16) NOT NULL,  -- 'wb' / 'ozon'
    external_id VARCHAR(64) NOT NULL,  -- SKU / артикул
    url TEXT NOT NULL,
    title TEXT,
    brand VARCHAR(255),
    category TEXT,
    price_kopecks INT,
    rating NUMERIC(2,1),
    reviews_count INT,
    last_parsed_at TIMESTAMPTZ,
    UNIQUE(marketplace, external_id)
);

CREATE INDEX idx_products_marketplace_external_id ON products(marketplace, external_id);

-- Запросы на анализ
CREATE TABLE analyses (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    product_id UUID REFERENCES products(id),
    input_url TEXT NOT NULL,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    -- pending / scraping / analyzing / completed / failed
    error_message TEXT,
    reviews_analyzed_count INT,
    llm_cost_kopecks INT,              -- для контроля экономики
    result JSONB,                      -- финальный отчёт
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);

CREATE INDEX idx_analyses_user_id ON analyses(user_id);
CREATE INDEX idx_analyses_status ON analyses(status);

-- Сырые отзывы (для кэша и аудита)
CREATE TABLE reviews (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    external_id VARCHAR(128),
    rating SMALLINT,
    text TEXT,
    pros TEXT,                         -- WB разделяет +/-
    cons TEXT,
    review_date TIMESTAMPTZ,
    fetched_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE(product_id, external_id)
);

CREATE INDEX idx_reviews_product_id ON reviews(product_id);

-- Платежи
CREATE TABLE payments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    yookassa_payment_id VARCHAR(64) UNIQUE,
    amount_kopecks INT NOT NULL,
    plan VARCHAR(32) NOT NULL,
    period_months INT NOT NULL DEFAULT 1,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    -- pending / succeeded / canceled / refunded
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    completed_at TIMESTAMPTZ
);
```

**Результат анализа (`analyses.result` JSONB) — структура:**

```json
{
  "summary": "Краткое резюме одним абзацем на 3-4 предложения",
  "product_info": {
    "title": "...",
    "brand": "...",
    "rating": 4.7,
    "reviews_analyzed": 312
  },
  "complaints": [
    {
      "topic": "Качество ткани",
      "frequency": 47,
      "severity": "high",
      "description": "Покупатели жалуются на тонкую ткань, просвечивает на свету.",
      "sample_quotes": ["Ткань очень тонкая...", "Просвечивает на солнце..."]
    }
  ],
  "praises": [
    {
      "topic": "Размер соответствует",
      "frequency": 89,
      "description": "Размерная сетка совпадает с указанной.",
      "sample_quotes": ["Размер сел как влитой..."]
    }
  ],
  "opportunities": [
    {
      "category": "product",
      "title": "Использовать более плотную ткань",
      "rationale": "47 жалоб на тонкость — крупнейшая проблема."
    },
    {
      "category": "card",
      "title": "Добавить фото на просвет",
      "rationale": "Селлер может закрыть возражение, показав плотность ткани."
    },
    {
      "category": "infographic",
      "title": "Слайд 'Размер соответствует' с метрикой '89% довольны размером'",
      "rationale": "Использовать сильную сторону для УТП."
    }
  ],
  "demographic_hints": "По отзывам прослеживается аудитория: мамы 25-40, преимущественно подарок.",
  "generated_at": "2026-..."
}
```

---

## 5. Backend — детали

### 5.1. Эндпоинты

```
# Auth
POST   /api/auth/telegram         # Тело: TG WebApp initData / Widget data. Возвращает JWT
POST   /api/auth/refresh          # Обновление токена
GET    /api/me                    # Профиль + подписка + лимиты

# Analyses
POST   /api/analyses              # Тело: {url}. Возвращает {id, status}. Запускает RQ-задачу
GET    /api/analyses              # Список своих анализов (пагинация)
GET    /api/analyses/{id}         # Статус и результат
DELETE /api/analyses/{id}         # Удалить анализ (опционально)

# Payments
POST   /api/payments              # Тело: {plan}. Возвращает {confirmation_url}
POST   /api/payments/webhook      # Вебхук ЮKassa (без auth, проверка по подписи)
GET    /api/payments              # История платежей

# Misc
GET    /api/health                # Для мониторинга
```

### 5.2. Авторизация через Telegram Login Widget

- Frontend использует [Telegram Login Widget](https://core.telegram.org/widgets/login) — кнопка "Войти через Telegram" на странице `/login`.
- TG возвращает payload с `id`, `first_name`, `username`, `photo_url`, `auth_date`, `hash`.
- Backend проверяет `hash` через HMAC-SHA256 с использованием SHA256 от bot token (см. документацию Telegram).
- При первом входе создаём `users` запись. Возвращаем JWT (access + refresh).
- JWT в `httpOnly` cookie + CSRF-токен, либо в Authorization header.

### 5.3. Логика анализа

`POST /api/analyses` делает:
1. Парсит URL → определяет маркетплейс и `external_id`.
2. Проверяет лимит пользователя (`analyses_used_this_period` < лимит по тарифу).
3. Создаёт запись в `analyses` со статусом `pending`.
4. Кладёт задачу в RQ-очередь.
5. Возвращает `{id, status: "pending"}`.

Воркер выполняет:
1. `status → scraping`
2. Парсит карточку и отзывы (см. раздел 7).
3. `status → analyzing`
4. Запускает LLM-пайплайн.
5. Сохраняет результат, `status → completed`.
6. При ошибке: `status → failed`, сохраняет `error_message`, **не списывает** анализ из лимита.

### 5.4. Конфигурация (.env)

```
DATABASE_URL=postgresql+asyncpg://user:pass@db:5432/reviewlens
REDIS_URL=redis://redis:6379/0
ANTHROPIC_API_KEY=sk-ant-...
TELEGRAM_BOT_TOKEN=...
JWT_SECRET=...
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=30
YOOKASSA_SHOP_ID=...
YOOKASSA_SECRET_KEY=...
FRONTEND_URL=https://reviewlens.ru
BACKEND_URL=https://api.reviewlens.ru
ENV=development
```

---

## 6. LLM-пайплайн

### 6.1. Стратегия

- **Модель для массовой обработки:** `claude-haiku-4-5` (дёшево, быстро, хорошо для классификации).
- **Модель для итогового отчёта:** `claude-sonnet-4-6` (один вызов, качественный синтез).
- Цель: ≤ 15 ₽ на полный анализ 300 отзывов.

### 6.2. Этапы

**Этап 1. Extract.** Делим отзывы на чанки по 30 штук. Для каждого чанка вызываем Haiku с промптом:

> Ты помогаешь продавцу на маркетплейсе анализировать отзывы конкурента. Вот {N} отзывов. Для каждого отзыва выдели:
> - claims_negative: список конкретных жалоб (по 3-7 слов каждая)
> - claims_positive: список конкретных похвал
> - emotional_tone: "positive" / "neutral" / "negative" / "mixed"
> Верни строго JSON массив объектов.

**Этап 2. Cluster.** Собираем все claims в один список (например, 800-1500 фраз). Одним вызовом Haiku:

> Вот список претензий покупателей. Кластеризуй похожие в группы. Для каждой группы укажи:
> - topic: короткое название (3-5 слов)
> - frequency: сколько фраз попало в группу
> - sample_quotes: 3 наиболее характерных
> Оставь только группы с frequency ≥ 3. Верни JSON.

Аналогично для positive.

**Этап 3. Synthesize.** Один вызов Sonnet с агрегатом + метаданными карточки. Промпт большой, в `prompts.py`. Просит сгенерировать итоговый `result` JSON по схеме из раздела 4. С низкой температурой (0.2).

### 6.3. Контроль стоимости

- Перед запуском проверяем оценку токенов; если > бюджета, обрезаем количество отзывов (берём свежие).
- В `analyses.llm_cost_kopecks` фиксируем фактическую стоимость по `usage` из ответов SDK.
- В админке (отдельная страница) видим среднюю стоимость анализа за период.

### 6.4. Тестирование промптов

Все промпты — в `app/llm/prompts.py` как константы. Создать `tests/test_prompts_e2e.py` с 3-5 реальными карточками-фикстурами (сохранёнными JSON отзывами), чтобы можно было итеративно улучшать промпты, не парся каждый раз заново.

---

## 7. Парсинг WB и Ozon

### 7.1. Wildberries

Отзывы доступны через публичные эндпоинты feedbacks (документации нет, но они открыты и стабильны на момент написания).

**Карточка товара:**
```
GET https://card.wb.ru/cards/v1/detail?appType=1&curr=rub&dest=-1257786&nm={article}
```

**Отзывы (feedbacks):**
```
GET https://feedbacks{1|2}.wb.ru/feedbacks/v1/{imt_id}
```
где `imt_id` берётся из ответа карточки (`data.products[0].root`).

Реализовать:
- Распарсить URL: `https://www.wildberries.ru/catalog/{article}/detail.aspx` → `article`.
- Запросить карточку, получить `imt_id`, основные поля.
- Запросить отзывы с двух хостов (feedbacks1 / feedbacks2), смержить, дедуплицировать.
- Лимит на анализ: 500 свежих отзывов.

### 7.2. Ozon

Сложнее, требуется headless-браузер либо использование внутреннего API через сессию. На первой фазе **поддерживаем только Wildberries**, кнопка Ozon в UI — disabled с пометкой "скоро".

### 7.3. Анти-блокировка

- User-Agent ротация (заранее список из 5–7 реальных).
- Простой rate limit: не более 2 RPS на хост.
- Retry с экспоненциальным backoff (3 попытки).
- Прокси на старте не нужен — публичные эндпоинты WB не блокируют умеренный трафик.

### 7.4. Кэширование

- Если карточка парсилась < 24 часов назад — используем кэш `products` + `reviews`.
- Если запрос на тот же URL от другого пользователя в кэше — анализ занимает 2 минуты вместо 5.

---

## 8. Платежи (ЮKassa)

### 8.1. Логика

1. Пользователь жмёт "Оформить подписку" на странице `/billing`.
2. POST `/api/payments` с `{plan: "starter"|"pro", period_months: 1}`.
3. Backend:
   - Создаёт `payments` со статусом `pending`.
   - Вызывает ЮKassa API: `create_payment(amount, description, confirmation: {type: "redirect", return_url})`.
   - Сохраняет `yookassa_payment_id`.
   - Возвращает `confirmation_url`.
4. Frontend редиректит на `confirmation_url`.
5. После оплаты ЮKassa дёргает `/api/payments/webhook`.
6. Backend проверяет подпись, обновляет `payments.status`, продлевает `users.subscription_until`, сбрасывает `analyses_used_this_period`.

### 8.2. Юридические моменты

- Принимать платежи может ИП или самозанятый. ЮKassa поддерживает обоих.
- В UI на этапе MVP — оферта и политика обработки ПД (черновики через LLM, потом юрист).
- Чек 54-ФЗ: ЮKassa умеет автоматически выбивать чек через интегрированную онлайн-кассу. Включить эту опцию.

---

## 9. Frontend — детали

### 9.1. Маршрутизация (App Router)

```
/                          # Лендинг
/login                     # Telegram Login Widget
/(app)/dashboard           # Список последних анализов + кнопка "Новый анализ"
/(app)/analyses/new        # Форма ввода URL
/(app)/analyses/[id]       # Страница отчёта (с polling статуса)
/(app)/billing             # Тарифы и история платежей
/(app)/settings            # Профиль, email для уведомлений
```

### 9.2. Ключевые экраны

**Лендинг (`/`):**
- Hero: "Узнайте, на что жалуются покупатели конкурентов — за 5 минут вместо 5 часов"
- 3 шага: вставь URL → подожди → получи отчёт
- Демо-отчёт (можно показать на фейковых данных)
- Цены (3 тарифа)
- FAQ
- Футер с офертой и политикой ПД

**Дашборд:**
- Кнопка "Новый анализ" (большая, по центру)
- Список последних 10 анализов: дата, товар, статус, кнопка "Открыть"
- Бейдж тарифа + остаток анализов

**Страница анализа `/analyses/[id]`:**
- Пока `status != completed` — анимированный прогресс с шагами:
  - "Парсим отзывы..." (20%)
  - "Анализируем 300 отзывов..." (60%)
  - "Готовим отчёт..." (90%)
  - Polling каждые 3 секунды через TanStack Query
- Когда `completed`:
  - Шапка: фото, название, рейтинг, кол-во проанализированных отзывов
  - Секция Summary (одним абзацем)
  - Секция "Жалобы" — карточки по убыванию частоты, с примерами
  - Секция "Хвалят за" — то же
  - Секция "Идеи для вас" — рекомендации по категориям (product / card / infographic)
  - Кнопка "Скачать PDF" (на будущее, в MVP — заглушка)

### 9.3. Визуальный стиль

- Свежий, неперегруженный, в духе Linear/Notion.
- Светлая тема + системный dark mode.
- Цветовая палитра: основной — глубокий синий (#2563eb), акцент — тёплый коралл (#f97316).
- Никаких "корпоративных" иллюстраций. Минимум иконок (Lucide). Карточки с мягкой тенью, скруглением 12px.

---

## 10. Запуск локально

```bash
# .env скопировать из .env.example, заполнить
docker-compose up -d
# инициализация БД
docker-compose exec backend alembic upgrade head
# создать тестового пользователя через CLI (опционально)
docker-compose exec backend python -m app.scripts.create_test_user
# фронт
docker-compose up frontend
```

`docker-compose.yml` должен включать: `db`, `redis`, `backend`, `worker`, `frontend`. Hot-reload для всех.

---

## 11. Фазы реализации

**Не начинай следующую фазу, пока предыдущая не работает end-to-end.**

### Фаза 1. Каркас (1–2 дня)
- [ ] Структура монорепо, docker-compose с db и redis
- [ ] FastAPI запускается, /api/health отдаёт 200
- [ ] Next.js запускается, лендинг (пока пустой) открывается
- [ ] Alembic настроен, пустая миграция применяется
- [ ] Базовая модель User, миграция

### Фаза 2. Авторизация (1 день)
- [ ] Telegram Login Widget на /login
- [ ] Эндпоинт /api/auth/telegram с проверкой hash
- [ ] JWT-токены, /api/me работает
- [ ] Защищённая зона /dashboard, редирект неавторизованных

### Фаза 3. Парсинг WB (2 дня)
- [ ] `WildberriesScraper` класс
- [ ] Парсинг карточки по URL
- [ ] Парсинг отзывов (500 шт)
- [ ] Тесты на 2-3 живых артикулах
- [ ] Сохранение в `products` и `reviews`

### Фаза 4. LLM-пайплайн (3 дня)
- [ ] Anthropic клиент в `app/llm/client.py`
- [ ] Промпты Extract / Cluster / Synthesize в `prompts.py`
- [ ] Pipeline в `pipeline.py`
- [ ] Тест на одной фикстуре (сохранённые JSON отзывы) — отчёт генерируется
- [ ] Замер стоимости и времени

### Фаза 5. Очередь и API анализов (1–2 дня)
- [ ] RQ worker запускается
- [ ] POST /api/analyses кладёт задачу
- [ ] Задача парсит и анализирует
- [ ] GET /api/analyses/{id} возвращает статус и результат
- [ ] Лимиты по тарифу проверяются

### Фаза 6. UI анализов (2 дня)
- [ ] Дашборд со списком
- [ ] Форма "Новый анализ"
- [ ] Страница анализа с polling
- [ ] Рендер всех секций результата

### Фаза 7. Платежи (2 дня)
- [ ] ЮKassa интеграция
- [ ] /api/payments создаёт платёж
- [ ] Вебхук подтверждения
- [ ] UI страницы /billing, тарифы
- [ ] Тест полного цикла (тестовый магазин ЮKassa)

### Фаза 8. Лендинг и полировка (2 дня)
- [ ] Лендинг с финальным копирайтом
- [ ] Демо-отчёт
- [ ] FAQ, оферта, политика ПД (заглушки)
- [ ] Email-уведомление при готовности анализа (опционально)
- [ ] Мобильная адаптация

### Фаза 9. Деплой (1 день)
- [ ] docker-compose.prod.yml
- [ ] Caddy/Nginx с автоматическим HTTPS
- [ ] Деплой на Selectel/Timeweb
- [ ] Домен, DNS
- [ ] Sentry для ошибок

**Итого:** 15–18 рабочих дней.

---

## 12. Acceptance criteria для MVP

MVP считается готовым, когда:

1. Новый пользователь может зайти, авторизоваться через Telegram.
2. Бесплатно сделать 1 анализ карточки WB по URL.
3. Получить отчёт за ≤ 5 минут с заполненными секциями жалоб/похвал/рекомендаций.
4. Оплатить тариф через ЮKassa, после чего лимит обновляется.
5. История анализов сохраняется и доступна в дашборде.
6. Стоимость LLM на один анализ — не выше 15 ₽.
7. Сервис работает на проде по HTTPS, ошибки логируются.

---

## 13. На что обратить внимание Claude Code

- **Не разворачивай скоуп.** Если по ходу появляется идея "а давай ещё добавим Ozon / мониторинг / экспорт в Excel" — пиши в `BACKLOG.md`, не делай.
- **Промпты в одном файле** `app/llm/prompts.py` как константы — это критично для итерации.
- **Параметризуй модели Claude через .env** — будем менять без передеплоя.
- **Все суммы — в копейках** (`int`), никаких `float` для денег.
- **JSON-схему результата зафиксируй как Pydantic-модель** — фронт должен иметь типы.
- **Логи в JSON** через `structlog` или `loguru` — на проде понадобится.
- **Не клади токены в git**. `.env.example` — да, `.env` — никогда.

---

Удачи. Если что-то непонятно — спрашивай у пользователя до того, как делать.
