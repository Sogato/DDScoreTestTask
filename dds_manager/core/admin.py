from django.contrib import admin
from .models import Status, Type, Category, Subcategory, Transaction


@admin.register(Status)
class StatusAdmin(admin.ModelAdmin):
    """Настройка админ-панели для справочника статусов."""

    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


@admin.register(Type)
class TypeAdmin(admin.ModelAdmin):
    """Настройка админ-панели для справочника типов операций."""

    list_display = ['name', 'slug']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """Настройка админ-панели для справочника категорий."""

    list_display = ['name', 'type', 'slug']
    list_filter = ['type']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']
    list_select_related = ['type']


@admin.register(Subcategory)
class SubcategoryAdmin(admin.ModelAdmin):
    """Настройка админ-панели для справочника подкатегорий."""

    list_display = ['name', 'category', 'get_type', 'slug']
    list_filter = ['category__type', 'category']
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'category__name']
    list_select_related = ['category', 'category__type']

    def get_type(self, obj):
        """Получение типа через связанную категорию для отображения в списке."""
        return obj.category.type.name

    get_type.short_description = 'Тип'
    get_type.admin_order_field = 'category__type'


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    """Настройка админ-панели для транзакций."""

    list_display = [
        'date', 'status', 'type', 'category', 'subcategory',
        'amount', 'comment_short'
    ]
    list_filter = [
        'date', 'status', 'type', 'category__type', 'category'
    ]
    search_fields = [
        'comment', 'category__name', 'subcategory__name'
    ]
    date_hierarchy = 'date'
    list_select_related = [
        'status', 'type', 'category', 'subcategory'
    ]
    autocomplete_fields = [
        'category', 'subcategory'
    ]
    readonly_fields = ['created_at'] if hasattr(Transaction, 'created_at') else []

    def comment_short(self, obj):
        """Сокращенный комментарий для отображения в списке (макс. 50 символов)."""
        if obj.comment:
            return obj.comment[:50] + '...' if len(obj.comment) > 50 else obj.comment
        return '-'

    comment_short.short_description = 'Комментарий'

    fieldsets = (
        ('Основная информация', {
            'fields': ('date', 'status', 'amount', 'comment')
        }),
        ('Классификация', {
            'fields': ('type', 'category', 'subcategory')
        }),
    )

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Динамическая фильтрация зависимых полей в админ-панели.

        При редактировании транзакции:
        - Категории фильтруются по выбранному типу
        - Подкатегории фильтруются по выбранной категории
        """
        obj_id = request.resolver_match.kwargs.get('object_id')

        if db_field.name == "category":
            if obj_id:
                try:
                    transaction = Transaction.objects.get(pk=obj_id)
                    if transaction.type:
                        kwargs["queryset"] = Category.objects.filter(type=transaction.type)
                except Transaction.DoesNotExist:
                    pass

        elif db_field.name == "subcategory":
            if obj_id:
                try:
                    transaction = Transaction.objects.get(pk=obj_id)
                    if transaction.category:
                        kwargs["queryset"] = Subcategory.objects.filter(category=transaction.category)
                except Transaction.DoesNotExist:
                    pass

        return super().formfield_for_foreignkey(db_field, request, **kwargs)
