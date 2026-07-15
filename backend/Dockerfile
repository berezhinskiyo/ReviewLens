FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app

WORKDIR /app

# git нужен для pip-установки общего пакета authbilling из GitHub (git+https)
RUN apt-get update && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

# Сначала зависимости — для кэширования слоя
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install -e .

# Сертификаты Russian Trusted CA (Минцифры) — нужны для TLS к API Т-Банка
# (securepay.tinkoff.ru). Ставим и в системное хранилище, и в bundle certifi,
# которым по умолчанию пользуется httpx.
# ВАЖНО: cacert.pem НЕ заканчивается переводом строки, поэтому голый `cat >>`
# склеивает "-----END CERTIFICATE----------BEGIN CERTIFICATE-----" в одну строку,
# и OpenSSL отвергает ВЕСЬ бандл (ssl.SSLError: [X509] PEM lib) — ломается любой
# httpx-запрос (OAuth, Т-Банк, Postbox, LLM). Поэтому дописываем \n перед каждым
# сертификатом и проверяем бандл на этапе сборки.
RUN set -eux; \
    apt-get update; apt-get install -y --no-install-recommends ca-certificates curl; \
    curl -fsSL https://gu-st.ru/content/lending/russian_trusted_root_ca_pem.crt -o /usr/local/share/ca-certificates/russian_trusted_root_ca.crt; \
    curl -fsSL https://gu-st.ru/content/lending/russian_trusted_sub_ca_pem.crt  -o /usr/local/share/ca-certificates/russian_trusted_sub_ca.crt; \
    update-ca-certificates; \
    BUNDLE="$(python -c 'import certifi; print(certifi.where())')"; \
    for c in /usr/local/share/ca-certificates/russian_trusted_root_ca.crt \
             /usr/local/share/ca-certificates/russian_trusted_sub_ca.crt; do \
        echo >> "$BUNDLE"; \
        cat "$c" >> "$BUNDLE"; \
    done; \
    python -c "import ssl, certifi; ssl.create_default_context(cafile=certifi.where()); print('CA bundle OK')"; \
    python -c "import httpx; httpx.Client(); print('httpx client OK')"; \
    rm -rf /var/lib/apt/lists/*

COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
