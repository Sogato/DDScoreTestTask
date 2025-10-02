from django import forms
from django.core.exceptions import ValidationError
from .models import Transaction, Status, Type, Category, Subcategory


class TransactionFilterForm(forms.Form):
    """
    Форма фильтрации транзакций на главной странице.

    Позволяет фильтровать по:
    - Периоду дат (дата с/по)
    - Статусу
    - Типу операции (с динамической загрузкой категорий)
    - Категории (с динамической загрузкой подкатегорий)
    - Подкатегории
    """

    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        label="Дата с"
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        }),
        label="Дата по"
    )
    status = forms.ModelChoiceField(
        queryset=Status.objects.all(),
        required=False,
        empty_label="Все статусы",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Статус"
    )
    type = forms.ModelChoiceField(
        queryset=Type.objects.all(),
        required=False,
        empty_label="Все типы",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'filter_type'
        }),
        label="Тип"
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="Сначала выберите тип",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'filter_category',
            'disabled': 'disabled'
        }),
        label="Категория"
    )
    subcategory = forms.ModelChoiceField(
        queryset=Subcategory.objects.all(),
        required=False,
        empty_label="Сначала выберите категорию",
        widget=forms.Select(attrs={
            'class': 'form-control',
            'id': 'filter_subcategory',
            'disabled': 'disabled'
        }),
        label="Подкатегория"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Обработка GET-параметров для сохранения состояния фильтров
        if self.data:
            try:
                type_id = self.data.get('type')
                if type_id:
                    type_id = int(type_id)
                    self.fields['category'].queryset = Category.objects.filter(type_id=type_id)
                    self.fields['category'].empty_label = "Все категории"
                    self.fields['category'].widget.attrs.pop('disabled', None)

                    category_id = self.data.get('category')
                    if category_id:
                        category_id = int(category_id)
                        self.fields['subcategory'].queryset = Subcategory.objects.filter(category_id=category_id)
                        self.fields['subcategory'].empty_label = "Все подкатегории"
                        self.fields['subcategory'].widget.attrs.pop('disabled', None)
                    else:
                        self.fields['subcategory'].queryset = Subcategory.objects.none()
                else:
                    self.fields['category'].queryset = Category.objects.none()
                    self.fields['subcategory'].queryset = Subcategory.objects.none()
            except (ValueError, TypeError):
                self.fields['category'].queryset = Category.objects.none()
                self.fields['subcategory'].queryset = Subcategory.objects.none()
        else:
            # При первой загрузке страницы зависимые поля пусты
            self.fields['category'].queryset = Category.objects.none()
            self.fields['subcategory'].queryset = Subcategory.objects.none()


class TransactionForm(forms.ModelForm):
    """
    Форма создания и редактирования транзакций.

    Реализует динамическую фильтрацию зависимых полей:
    - При выборе типа через AJAX загружаются соответствующие категории
    - При выборе категории через AJAX загружаются соответствующие подкатегории
    """

    class Meta:
        model = Transaction
        fields = ['date', 'status', 'type', 'category', 'subcategory', 'amount', 'comment']
        widgets = {
            'date': forms.DateInput(attrs={
                'type': 'date',
                'class': 'form-control'
            }),
            'status': forms.Select(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_type'
            }),
            'category': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_category'
            }),
            'subcategory': forms.Select(attrs={
                'class': 'form-control',
                'id': 'id_subcategory'
            }),
            'amount': forms.NumberInput(attrs={
                'class': 'form-control',
                'step': '0.01',
                'min': '0'
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Настройка формата даты для HTML5 input type="date"
        self.fields['date'].widget.format = '%Y-%m-%d'
        self.fields['date'].input_formats = ['%Y-%m-%d']

        # Подсказки для зависимых полей
        self.fields['category'].empty_label = "Сначала выберите тип"
        self.fields['subcategory'].empty_label = "Сначала выберите категорию"

        # Редактирование существующей транзакции
        if self.instance.pk:
            if self.data:
                # POST-запрос: обрабатываем отправленные данные
                try:
                    type_id = int(self.data.get('type'))
                    self.fields['category'].queryset = Category.objects.filter(type_id=type_id)
                    self.fields['category'].empty_label = "---------"

                    category_id = self.data.get('category')
                    if category_id:
                        category_id = int(category_id)
                        self.fields['subcategory'].queryset = Subcategory.objects.filter(category_id=category_id)
                        self.fields['subcategory'].empty_label = "---------"
                    else:
                        self.fields['subcategory'].queryset = Subcategory.objects.none()
                except (ValueError, TypeError, KeyError):
                    # При ошибке используем текущие значения из instance
                    if self.instance.type:
                        self.fields['category'].queryset = Category.objects.filter(
                            type=self.instance.type
                        )
                        self.fields['category'].empty_label = "---------"
                    if self.instance.category:
                        self.fields['subcategory'].queryset = Subcategory.objects.filter(
                            category=self.instance.category
                        )
                        self.fields['subcategory'].empty_label = "---------"
            else:
                # GET-запрос: загружаем форму с текущими значениями
                if self.instance.type:
                    self.fields['category'].queryset = Category.objects.filter(
                        type=self.instance.type
                    )
                    self.fields['category'].empty_label = "---------"
                if self.instance.category:
                    self.fields['subcategory'].queryset = Subcategory.objects.filter(
                        category=self.instance.category
                    )
                    self.fields['subcategory'].empty_label = "---------"
        else:
            # Создание новой транзакции
            if self.data:
                # POST-запрос: обрабатываем отправленные данные
                try:
                    type_id = int(self.data.get('type'))
                    self.fields['category'].queryset = Category.objects.filter(type_id=type_id)
                    self.fields['category'].empty_label = "---------"

                    category_id = self.data.get('category')
                    if category_id:
                        category_id = int(category_id)
                        self.fields['subcategory'].queryset = Subcategory.objects.filter(category_id=category_id)
                        self.fields['subcategory'].empty_label = "---------"
                    else:
                        self.fields['subcategory'].queryset = Subcategory.objects.none()
                except (ValueError, TypeError, KeyError):
                    self.fields['category'].queryset = Category.objects.none()
                    self.fields['subcategory'].queryset = Subcategory.objects.none()
            else:
                # GET-запрос: пустая форма с пустыми зависимыми полями
                self.fields['category'].queryset = Category.objects.none()
                self.fields['subcategory'].queryset = Subcategory.objects.none()

    def clean(self):
        """
        Валидация иерархических зависимостей.

        Проверяет:
        - Категория должна принадлежать выбранному типу
        - Подкатегория должна принадлежать выбранной категории
        """
        cleaned_data = super().clean()
        type_obj = cleaned_data.get('type')
        category = cleaned_data.get('category')
        subcategory = cleaned_data.get('subcategory')

        if category and type_obj and category.type != type_obj:
            raise ValidationError(
                'Категория должна принадлежать выбранному типу.'
            )

        if subcategory and category and subcategory.category != category:
            raise ValidationError(
                'Подкатегория должна принадлежать выбранной категории.'
            )

        return cleaned_data


class StatusForm(forms.ModelForm):
    """Форма для создания и редактирования статусов."""

    class Meta:
        model = Status
        fields = ['name', 'slug']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
        }


class TypeForm(forms.ModelForm):
    """Форма для создания и редактирования типов операций."""

    class Meta:
        model = Type
        fields = ['name', 'slug']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
        }


class CategoryForm(forms.ModelForm):
    """Форма для создания и редактирования категорий."""

    class Meta:
        model = Category
        fields = ['name', 'slug', 'type']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-control'}),
        }


class SubcategoryForm(forms.ModelForm):
    """Форма для создания и редактирования подкатегорий."""

    class Meta:
        model = Subcategory
        fields = ['name', 'slug', 'category']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
        }
