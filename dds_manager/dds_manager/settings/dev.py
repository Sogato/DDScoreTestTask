"""
Настройки для окружения разработки (development).

DEBUG включен, используется для локальной разработки.
"""

from .base import *

# Разработка: включен debug-режим
DEBUG = True

# Разрешенные хосты для dev
ALLOWED_HOSTS = ['localhost', '127.0.0.1']
