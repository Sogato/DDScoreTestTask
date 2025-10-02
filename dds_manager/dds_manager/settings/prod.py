"""
Настройки для production окружения.

DEBUG отключен, настроены параметры безопасности для продакшена.
ALLOWED_HOSTS и пути к статическим файлам берутся из переменных окружения.
"""

from .base import *

# Production: отключен debug-режим
DEBUG = False

# Разрешенные хосты: из переменных окружения (список через запятую)
ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '').split(',')

# Настройки безопасности для теоретического production
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')  # Для прокси (Nginx)
SECURE_SSL_REDIRECT = True  # Перенаправление на HTTPS
SESSION_COOKIE_SECURE = True  # Куки сессий только по HTTPS
CSRF_COOKIE_SECURE = True  # CSRF-куки только по HTTPS
SECURE_BROWSER_XSS_FILTER = True  # Защита от XSS
SECURE_HSTS_INCLUDE_SUBDOMAINS = True  # HSTS для поддоменов
SECURE_HSTS_SECONDS = 31536000  # HSTS на 1 год
SECURE_HSTS_PRELOAD = True  # Разрешить предзагрузку HSTS
X_FRAME_OPTIONS = 'DENY'  # Запрет встраивания в фреймы

# Пути для static и media в production (сервируются через Nginx)
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_ROOT = BASE_DIR / 'media'
