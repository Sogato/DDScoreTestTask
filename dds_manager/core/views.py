from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q
from .models import Transaction, Status, Type, Category, Subcategory
from .forms import (
    TransactionForm, TransactionFilterForm, StatusForm,
    TypeForm, CategoryForm, SubcategoryForm
)


def transaction_list(request):
    """Главная страница со списком транзакций и фильтрацией"""
    transactions = Transaction.objects.select_related(
        'status', 'type', 'category', 'subcategory'
    ).all()

    filter_form = TransactionFilterForm(request.GET)

    if filter_form.is_valid():
        # Применяем фильтры
        if filter_form.cleaned_data.get('date_from'):
            transactions = transactions.filter(date__gte=filter_form.cleaned_data['date_from'])

        if filter_form.cleaned_data.get('date_to'):
            transactions = transactions.filter(date__lte=filter_form.cleaned_data['date_to'])

        if filter_form.cleaned_data.get('status'):
            transactions = transactions.filter(status=filter_form.cleaned_data['status'])

        if filter_form.cleaned_data.get('type'):
            transactions = transactions.filter(type=filter_form.cleaned_data['type'])

        if filter_form.cleaned_data.get('category'):
            transactions = transactions.filter(category=filter_form.cleaned_data['category'])

        if filter_form.cleaned_data.get('subcategory'):
            transactions = transactions.filter(subcategory=filter_form.cleaned_data['subcategory'])

    # Сортируем по дате (новые сначала)
    transactions = transactions.order_by('-date', '-id')

    context = {
        'transactions': transactions,
        'filter_form': filter_form,
    }

    return render(request, 'core/transaction_list.html', context)


def transaction_create(request):
    """Создание новой транзакции"""
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            transaction = form.save()
            messages.success(request, 'Транзакция успешно создана!')
            return redirect('transaction_list')
    else:
        form = TransactionForm()

    context = {
        'form': form,
        'title': 'Создание транзакции',
        'submit_text': 'Создать'
    }

    return render(request, 'core/transaction_form.html', context)


def transaction_update(request, pk):
    """Редактирование транзакции"""
    transaction = get_object_or_404(Transaction, pk=pk)

    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction)
        if form.is_valid():
            form.save()
            messages.success(request, 'Транзакция успешно обновлена!')
            return redirect('transaction_list')
    else:
        form = TransactionForm(instance=transaction)

    context = {
        'form': form,
        'transaction': transaction,
        'title': 'Редактирование транзакции',
        'submit_text': 'Сохранить'
    }

    return render(request, 'core/transaction_form.html', context)


def transaction_delete(request, pk):
    """Удаление транзакции"""
    transaction = get_object_or_404(Transaction, pk=pk)

    if request.method == 'POST':
        transaction.delete()
        messages.success(request, 'Транзакция успешно удалена!')
        return redirect('transaction_list')

    context = {
        'transaction': transaction,
    }

    return render(request, 'core/transaction_confirm_delete.html', context)


# AJAX views для зависимых селектов
def load_categories(request):
    """AJAX: загрузка категорий по типу"""
    type_id = request.GET.get('type_id')
    categories = Category.objects.filter(type_id=type_id).order_by('name')

    data = [{'id': cat.id, 'name': cat.name} for cat in categories]
    return JsonResponse(data, safe=False)


def load_subcategories(request):
    """AJAX: загрузка подкатегорий по категории"""
    category_id = request.GET.get('category_id')
    subcategories = Subcategory.objects.filter(category_id=category_id).order_by('name')

    data = [{'id': subcat.id, 'name': subcat.name} for subcat in subcategories]
    return JsonResponse(data, safe=False)


# Views для управления справочниками
def references_list(request):
    """Страница управления справочниками"""
    context = {
        'statuses': Status.objects.all(),
        'types': Type.objects.all(),
        'categories': Category.objects.select_related('type').all(),
        'subcategories': Subcategory.objects.select_related('category').all(),
    }

    return render(request, 'core/references_list.html', context)


# Status CRUD
class StatusCreateView(CreateView):
    model = Status
    form_class = StatusForm
    template_name = 'core/reference_form.html'
    success_url = reverse_lazy('references_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Создание статуса'
        context['submit_text'] = 'Создать'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Статус успешно создан!')
        return super().form_valid(form)


class StatusUpdateView(UpdateView):
    model = Status
    form_class = StatusForm
    template_name = 'core/reference_form.html'
    success_url = reverse_lazy('references_list')
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Редактирование статуса "{self.object.name}"'
        context['submit_text'] = 'Сохранить'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Статус успешно обновлен!')
        return super().form_valid(form)


class StatusDeleteView(DeleteView):
    model = Status
    template_name = 'core/reference_confirm_delete.html'
    success_url = reverse_lazy('references_list')
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_type'] = 'статус'
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Статус успешно удален!')
        return super().delete(request, *args, **kwargs)


# Type CRUD
class TypeCreateView(CreateView):
    model = Type
    form_class = TypeForm
    template_name = 'core/reference_form.html'
    success_url = reverse_lazy('references_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Создание типа'
        context['submit_text'] = 'Создать'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Тип успешно создан!')
        return super().form_valid(form)


class TypeUpdateView(UpdateView):
    model = Type
    form_class = TypeForm
    template_name = 'core/reference_form.html'
    success_url = reverse_lazy('references_list')
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Редактирование типа "{self.object.name}"'
        context['submit_text'] = 'Сохранить'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Тип успешно обновлен!')
        return super().form_valid(form)


class TypeDeleteView(DeleteView):
    model = Type
    template_name = 'core/reference_confirm_delete.html'
    success_url = reverse_lazy('references_list')
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_type'] = 'тип'
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Тип успешно удален!')
        return super().delete(request, *args, **kwargs)


# Category CRUD
class CategoryCreateView(CreateView):
    model = Category
    form_class = CategoryForm
    template_name = 'core/reference_form.html'
    success_url = reverse_lazy('references_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Создание категории'
        context['submit_text'] = 'Создать'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Категория успешно создана!')
        return super().form_valid(form)


class CategoryUpdateView(UpdateView):
    model = Category
    form_class = CategoryForm
    template_name = 'core/reference_form.html'
    success_url = reverse_lazy('references_list')
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Редактирование категории "{self.object.name}"'
        context['submit_text'] = 'Сохранить'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Категория успешно обновлена!')
        return super().form_valid(form)


class CategoryDeleteView(DeleteView):
    model = Category
    template_name = 'core/reference_confirm_delete.html'
    success_url = reverse_lazy('references_list')
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_type'] = 'категорию'
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Категория успешно удалена!')
        return super().delete(request, *args, **kwargs)


# Subcategory CRUD
class SubcategoryCreateView(CreateView):
    model = Subcategory
    form_class = SubcategoryForm
    template_name = 'core/reference_form.html'
    success_url = reverse_lazy('references_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = 'Создание подкатегории'
        context['submit_text'] = 'Создать'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Подкатегория успешно создана!')
        return super().form_valid(form)


class SubcategoryUpdateView(UpdateView):
    model = Subcategory
    form_class = SubcategoryForm
    template_name = 'core/reference_form.html'
    success_url = reverse_lazy('references_list')
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['title'] = f'Редактирование подкатегории "{self.object.name}"'
        context['submit_text'] = 'Сохранить'
        return context

    def form_valid(self, form):
        messages.success(self.request, 'Подкатегория успешно обновлена!')
        return super().form_valid(form)


class SubcategoryDeleteView(DeleteView):
    model = Subcategory
    template_name = 'core/reference_confirm_delete.html'
    success_url = reverse_lazy('references_list')
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_type'] = 'подкатегорию'
        return context

    def delete(self, request, *args, **kwargs):
        messages.success(request, 'Подкатегория успешно удалена!')
        return super().delete(request, *args, **kwargs)
