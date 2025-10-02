"""
Конфигурация приложения core.

Основное приложение для управления движением денежных средств (ДДС).
"""

from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Конфигурация приложения для учета транзакций ДДС."""

    default_auto_field = 'django.db.models.BigAutoField'
    name = 'core'
    verbose_name = 'Движение денежных средств'
