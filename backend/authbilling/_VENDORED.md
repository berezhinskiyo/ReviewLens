# Вендоренная копия

Это копия пакета `authbilling` из `my_lab/auth-billing-core/` (источник истины).
Вкладывается в проект, чтобы `docker build` работал без внешнего build-контекста.

При изменении пакета в источнике пересинхронизировать:
    rsync -a --exclude='__pycache__' ../../auth-billing-core/authbilling/ ./authbilling/
