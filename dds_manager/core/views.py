from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.http import JsonResponse
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from .models import Transaction, Status, Type, Category, Subcategory
from .forms import (
    TransactionForm, TransactionFilterForm, StatusForm,
    TypeForm, CategoryForm, SubcategoryForm
)


def transaction_list(request):
    """
    Главная страница со списком транзакций и фильтрацией.

    Отображает все транзакции с возможностью фильтрации по:
    - периоду дат (дата с/по)
    - статусу
    - типу операции
    - категории
    - подкатегории

    Также выводит статистику по количеству пополнений и списаний.
    """
    transactions = Transaction.objects.select_related(
        'status', 'type', 'category', 'subcategory'
    ).all()

    filter_form = TransactionFilterForm(request.GET)

    if filter_form.is_valid():
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

    transactions = transactions.order_by('-date', '-id')

    # Подсчет статистики (используется slug для независимости от названий типов)
    income_count = transactions.filter(type__slug='popolnenie').count()
    expense_count = transactions.filter(type__slug='spisanie').count()

    context = {
        'transactions': transactions,
        'filter_form': filter_form,
        'income_count': income_count,
        'expense_count': expense_count,
    }

    return render(request, 'core/transaction_list.html', context)


def transaction_create(request):
    """
    Создание новой транзакции.

    GET: отображает форму создания
    POST: сохраняет новую транзакцию и перенаправляет на список
    """
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        if form.is_valid():
            form.save()
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
    """
    Редактирование существующей транзакции.

    GET: отображает форму с текущими данными транзакции
    POST: сохраняет изменения и перенаправляет на список
    """
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
    """
    Удаление транзакции с подтверждением.

    GET: отображает страницу подтверждения удаления
    POST: удаляет транзакцию и перенаправляет на список
    """
    transaction = get_object_or_404(Transaction, pk=pk)

    if request.method == 'POST':
        transaction.delete()
        messages.success(request, 'Транзакция успешно удалена!')
        return redirect('transaction_list')

    context = {
        'transaction': transaction,
    }

    return render(request, 'core/transaction_confirm_delete.html', context)


def load_categories(request):
    """
    AJAX endpoint для загрузки категорий, привязанных к выбранному типу.

    Query параметры:
        type_id: ID типа операции

    Returns:
        JsonResponse: список категорий в формате [{"id": 1, "name": "Название"}, ...]
    """
    type_id = request.GET.get('type_id')
    categories = Category.objects.filter(type_id=type_id).order_by('name')

    data = [{'id': cat.id, 'name': cat.name} for cat in categories]
    return JsonResponse(data, safe=False)


def load_subcategories(request):
    """
    AJAX endpoint для загрузки подкатегорий, привязанных к выбранной категории.

    Query параметры:
        category_id: ID категории

    Returns:
        JsonResponse: список подкатегорий в формате [{"id": 1, "name": "Название"}, ...]
    """
    category_id = request.GET.get('category_id')
    subcategories = Subcategory.objects.filter(category_id=category_id).order_by('name')

    data = [{'id': subcat.id, 'name': subcat.name} for subcat in subcategories]
    return JsonResponse(data, safe=False)


def references_list(request):
    """
    Страница управления справочниками.

    Отображает все справочники системы:
    - Статусы
    - Типы операций
    - Категории (с привязкой к типам)
    - Подкатегории (с привязкой к категориям)
    """
    context = {
        'statuses': Status.objects.all(),
        'types': Type.objects.all(),
        'categories': Category.objects.select_related('type').all(),
        'subcategories': Subcategory.objects.select_related('category').all(),
    }

    return render(request, 'core/references_list.html', context)


# ==================== CRUD для справочника "Статусы" ====================

class StatusCreateView(CreateView):
    """Создание нового статуса."""

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
    """Редактирование существующего статуса."""

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
    """Удаление статуса с проверкой на использование в транзакциях."""

    model = Status
    template_name = 'core/reference_confirm_delete.html'
    success_url = reverse_lazy('references_list')
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_type'] = 'статус'
        return context

    def form_valid(self, form):
        try:
            result = super().form_valid(form)
            messages.success(self.request, 'Статус успешно удален!')
            return result
        except ProtectedError:
            messages.error(
                self.request,
                f'Невозможно удалить статус "{self.object.name}", '
                f'так как он используется в существующих транзакциях. '
                f'Сначала удалите или измените все связанные транзакции.'
            )
            return redirect('references_list')


# ==================== CRUD для справочника "Типы" ====================

class TypeCreateView(CreateView):
    """Создание нового типа операции."""

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
    """Редактирование существующего типа операции."""

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
    """Удаление типа с проверкой на использование в категориях и транзакциях."""

    model = Type
    template_name = 'core/reference_confirm_delete.html'
    success_url = reverse_lazy('references_list')
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_type'] = 'тип'
        return context

    def form_valid(self, form):
        try:
            result = super().form_valid(form)
            messages.success(self.request, 'Тип успешно удален!')
            return result
        except ProtectedError:
            messages.error(
                self.request,
                f'Невозможно удалить тип "{self.object.name}", '
                f'так как он используется в категориях или транзакциях. '
                f'Сначала удалите или измените все связанные записи.'
            )
            return redirect('references_list')


# ==================== CRUD для справочника "Категории" ====================

class CategoryCreateView(CreateView):
    """Создание новой категории."""

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
    """Редактирование существующей категории."""

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
    """Удаление категории с проверкой на использование в подкатегориях и транзакциях."""

    model = Category
    template_name = 'core/reference_confirm_delete.html'
    success_url = reverse_lazy('references_list')
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_type'] = 'категорию'
        return context

    def form_valid(self, form):
        try:
            result = super().form_valid(form)
            messages.success(self.request, 'Категория успешно удалена!')
            return result
        except ProtectedError:
            messages.error(
                self.request,
                f'Невозможно удалить категорию "{self.object.name}", '
                f'так как она используется в подкатегориях или транзакциях. '
                f'Сначала удалите или измените все связанные записи.'
            )
            return redirect('references_list')


# ==================== CRUD для справочника "Подкатегории" ====================

class SubcategoryCreateView(CreateView):
    """Создание новой подкатегории."""

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
    """Редактирование существующей подкатегории."""

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
    """Удаление подкатегории с проверкой на использование в транзакциях."""

    model = Subcategory
    template_name = 'core/reference_confirm_delete.html'
    success_url = reverse_lazy('references_list')
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['object_type'] = 'подкатегорию'
        return context

    def form_valid(self, form):
        try:
            result = super().form_valid(form)
            messages.success(self.request, 'Подкатегория успешно удалена!')
            return result
        except ProtectedError:
            messages.error(
                self.request,
                f'Невозможно удалить подкатегорию "{self.object.name}", '
                f'так как она используется в существующих транзакциях. '
                f'Сначала удалите или измените все связанные транзакции.'
            )
            return redirect('references_list')
