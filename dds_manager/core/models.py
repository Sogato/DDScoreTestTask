from django.db import models
from django.utils import timezone
from django.core.exceptions import ValidationError


class Status(models.Model):
    """
    Справочник статусов транзакций (Бизнес, Личное, Налог и т.д.).

    Используется для категоризации транзакций по назначению.
    Список статусов может расширяться пользователем.
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
    Справочник типов операций (Пополнение, Списание).

    Определяет направление денежного потока.
    Категории привязываются к конкретным типам.
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
    Справочник категорий транзакций (Инфраструктура, Маркетинг и т.д.).

    Категория обязательно привязана к типу операции.
    Например, категория "Маркетинг" может относиться только к типу "Списание".
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
        # Одно название категории может использоваться для разных типов
        unique_together = ["name", "type"]


class Subcategory(models.Model):
    """
    Справочник подкатегорий (VPS, Proxy, Farpost, Avito и т.д.).

    Подкатегория привязана к конкретной категории для детализации учета.
    Например, подкатегории "VPS" и "Proxy" относятся к категории "Инфраструктура".
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
        # Одно название подкатегории может использоваться для разных категорий
        unique_together = ["name", "category"]


class Transaction(models.Model):
    """
    Запись о движении денежных средств (ДДС).

    Основная модель приложения. Хранит информацию о денежной операции
    с привязкой к статусу, типу, категории и подкатегории.
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
        max_digits=15,
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
        Валидация иерархических зависимостей между сущностями.

        Проверяет:
        - Категория должна принадлежать выбранному типу
        - Подкатегория должна принадлежать выбранной категории

        Raises:
            ValidationError: Если нарушены зависимости между сущностями
        """
        errors = {}

        if self.category_id and self.type_id:
            try:
                # Используем select_related для минимизации запросов к БД
                category = Category.objects.select_related('type').get(id=self.category_id)
                if category.type_id != self.type_id:
                    errors['category'] = 'Категория должна принадлежать выбранному типу.'
            except Category.DoesNotExist:
                errors['category'] = 'Выбранная категория не существует.'

        if self.subcategory_id and self.category_id:
            try:
                # Используем select_related для минимизации запросов к БД
                subcategory = Subcategory.objects.select_related('category').get(id=self.subcategory_id)
                if subcategory.category_id != self.category_id:
                    errors['subcategory'] = 'Подкатегория должна принадлежать выбранной категории.'
            except Subcategory.DoesNotExist:
                errors['subcategory'] = 'Выбранная подкатегория не существует.'

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return f"{self.date} - {self.amount} руб. ({self.type})"

    class Meta:
        verbose_name = "Транзакция"
        verbose_name_plural = "Транзакции"
        ordering = ['-date', '-id']
