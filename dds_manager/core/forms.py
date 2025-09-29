from django import forms
from django.core.exceptions import ValidationError
from .models import Transaction, Status, Type, Category, Subcategory


class TransactionFilterForm(forms.Form):
    """Форма для фильтрации транзакций"""
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
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Тип"
    )
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="Все категории",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Категория"
    )
    subcategory = forms.ModelChoiceField(
        queryset=Subcategory.objects.all(),
        required=False,
        empty_label="Все подкатегории",
        widget=forms.Select(attrs={'class': 'form-control'}),
        label="Подкатегория"
    )


class TransactionForm(forms.ModelForm):
    """Форма для создания и редактирования транзакций"""

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

        # Если это редактирование существующей транзакции
        if self.instance.pk:
            # Фильтруем категории по выбранному типу
            if self.instance.type:
                self.fields['category'].queryset = Category.objects.filter(
                    type=self.instance.type
                )
            # Фильтруем подкатегории по выбранной категории
            if self.instance.category:
                self.fields['subcategory'].queryset = Subcategory.objects.filter(
                    category=self.instance.category
                )
        else:
            # Для новой транзакции показываем пустые списки
            self.fields['category'].queryset = Category.objects.none()
            self.fields['subcategory'].queryset = Subcategory.objects.none()

    def clean(self):
        cleaned_data = super().clean()
        type_obj = cleaned_data.get('type')
        category = cleaned_data.get('category')
        subcategory = cleaned_data.get('subcategory')

        # Проверяем, что категория принадлежит выбранному типу
        if category and type_obj and category.type != type_obj:
            raise ValidationError(
                'Категория должна принадлежать выбранному типу.'
            )

        # Проверяем, что подкатегория принадлежит выбранной категории
        if subcategory and category and subcategory.category != category:
            raise ValidationError(
                'Подкатегория должна принадлежать выбранной категории.'
            )

        return cleaned_data


# Формы для управления справочниками
class StatusForm(forms.ModelForm):
    class Meta:
        model = Status
        fields = ['name', 'slug']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
        }


class TypeForm(forms.ModelForm):
    class Meta:
        model = Type
        fields = ['name', 'slug']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
        }


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'slug', 'type']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'type': forms.Select(attrs={'class': 'form-control'}),
        }


class SubcategoryForm(forms.ModelForm):
    class Meta:
        model = Subcategory
        fields = ['name', 'slug', 'category']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control'}),
            'category': forms.Select(attrs={'class': 'form-control'}),
        }