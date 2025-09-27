from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError


class Status(models.Model):
    """
    Модель для справочника статусов (например, Бизнес, Личное, Налог).
    Поддерживает расширение списка.
    """
    name = models.CharField(max_length=50, unique=True, verbose_name="Название статуса")
    slug = models.SlugField(max_length=50, unique=True, verbose_name="Слаг")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Статус"
        verbose_name_plural = "Статусы"


class Type(models.Model):
    """
    Модель для справочника типов (например, Пополнение, Списание).
    Поддерживает расширение списка.
    """
    name = models.CharField(max_length=50, unique=True, verbose_name="Название типа")
    slug = models.SlugField(max_length=50, unique=True, verbose_name="Слаг")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Тип"
        verbose_name_plural = "Типы"


class Category(models.Model):
    """
    Модель для категорий (например, Инфраструктура, Маркетинг).
    Привязана к типу (например, Маркетинг относится к Списанию).
    """
    name = models.CharField(max_length=100, verbose_name="Название категории")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="Слаг")
    type = models.ForeignKey(
        Type,
        on_delete=models.CASCADE,
        related_name="categories",
        verbose_name="Тип",
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Категория"
        verbose_name_plural = "Категории"
        unique_together = ["name", "type"]  # Уникальность имени в рамках типа


class Subcategory(models.Model):
    """
    Модель для подкатегорий (например, VPS, Proxy для Инфраструктуры).
    Привязана к категории.
    """
    name = models.CharField(max_length=100, verbose_name="Название подкатегории")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="Слаг")
    category = models.ForeignKey(
        Category,
        on_delete=models.CASCADE,
        related_name="subcategories",
        verbose_name="Категория",
    )

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Подкатегория"
        verbose_name_plural = "Подкатегории"
        unique_together = ["name", "category"]  # Уникальность имени в рамках категории


class Transaction(models.Model):
    """
    Модель для записи о движении денежных средств (ДДС).
    Содержит дату, статус, тип, категорию, подкатегорию, сумму и комментарий.
    """
    date = models.DateField(
        default=timezone.now,
        verbose_name="Дата",
        help_text="Дата создания записи, автоматически заполняется текущей датой.",
    )
    status = models.ForeignKey(
        Status,
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name="Статус",
    )
    type = models.ForeignKey(
        Type,
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name="Тип",
    )
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name="Категория",
    )
    subcategory = models.ForeignKey(
        Subcategory,
        on_delete=models.PROTECT,
        related_name="transactions",
        verbose_name="Подкатегория",
    )
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Сумма",
        help_text="Сумма в рублях.",
    )
    comment = models.TextField(
        blank=True,
        verbose_name="Комментарий",
        help_text="Необязательный комментарий к записи.",
    )

    def clean(self):
        """
        Валидация зависимостей: подкатегория должна принадлежать выбранной категории,
        категория — выбранному типу.
        """
        if self.subcategory and self.subcategory.category != self.category:
            raise ValidationError(
                {"subcategory": "Подкатегория должна принадлежать выбранной категории."}
            )
        if self.category and self.category.type != self.type:
            raise ValidationError(
                {"category": "Категория должна принадлежать выбранному типу."}
            )

    def __str__(self):
        return f"{self.date} - {self.amount} руб. ({self.type})"

    class Meta:
        verbose_name = "Транзакция"
        verbose_name_plural = "Транзакции"