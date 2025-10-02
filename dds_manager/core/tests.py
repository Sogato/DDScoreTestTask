from django.test import TestCase, Client
from django.urls import reverse
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from decimal import Decimal
from datetime import date, timedelta
import json

from .models import Status, Type, Category, Subcategory, Transaction
from .forms import TransactionForm, TransactionFilterForm


class ModelsTestCase(TestCase):
    """Тесты моделей данных и их валидации."""

    def setUp(self):
        """Создание базовых тестовых объектов перед каждым тестом."""
        self.status = Status.objects.create(name='Бизнес', slug='business')
        self.income_type = Type.objects.create(name='Пополнение', slug='income')
        self.expense_type = Type.objects.create(name='Списание', slug='expense')

        self.income_category = Category.objects.create(
            name='Продажи', slug='sales', type=self.income_type
        )
        self.expense_category = Category.objects.create(
            name='Маркетинг', slug='marketing', type=self.expense_type
        )

        self.income_subcategory = Subcategory.objects.create(
            name='Онлайн продажи', slug='online-sales', category=self.income_category
        )
        self.expense_subcategory = Subcategory.objects.create(
            name='Avito', slug='avito', category=self.expense_category
        )

    def test_status_creation(self):
        """Тест создания статуса и его строкового представления."""
        status = Status.objects.create(name='Личное', slug='personal')
        self.assertEqual(status.name, 'Личное')
        self.assertEqual(str(status), 'Личное')

    def test_type_creation(self):
        """Тест создания типа операции."""
        self.assertEqual(str(self.income_type), 'Пополнение')
        self.assertEqual(self.income_type.slug, 'income')

    def test_category_type_relationship(self):
        """Тест связи категории с типом операции."""
        self.assertEqual(self.income_category.type, self.income_type)
        self.assertIn(self.income_category, self.income_type.categories.all())

    def test_subcategory_category_relationship(self):
        """Тест связи подкатегории с категорией."""
        self.assertEqual(self.income_subcategory.category, self.income_category)
        self.assertIn(self.income_subcategory, self.income_category.subcategories.all())

    def test_transaction_creation_valid(self):
        """Тест создания валидной транзакции."""
        transaction = Transaction.objects.create(
            date=date.today(),
            status=self.status,
            type=self.income_type,
            category=self.income_category,
            subcategory=self.income_subcategory,
            amount=Decimal('1000.00'),
            comment='Тестовая транзакция'
        )

        self.assertEqual(transaction.amount, Decimal('1000.00'))
        self.assertEqual(transaction.status, self.status)
        self.assertTrue('1000' in str(transaction))

    def test_transaction_validation_subcategory_mismatch(self):
        """Тест валидации: подкатегория должна принадлежать выбранной категории."""
        transaction = Transaction(
            date=date.today(),
            status=self.status,
            type=self.income_type,
            category=self.income_category,
            subcategory=self.expense_subcategory,
            amount=Decimal('1000.00')
        )

        with self.assertRaises(ValidationError) as cm:
            transaction.full_clean()

        self.assertIn('subcategory', cm.exception.message_dict)

    def test_transaction_validation_category_mismatch(self):
        """Тест валидации: категория должна принадлежать выбранному типу."""
        transaction = Transaction(
            date=date.today(),
            status=self.status,
            type=self.income_type,
            category=self.expense_category,
            subcategory=self.income_subcategory,
            amount=Decimal('1000.00')
        )

        with self.assertRaises(ValidationError) as cm:
            transaction.full_clean()

        self.assertIn('category', cm.exception.message_dict)

    def test_unique_constraints_same_type(self):
        """Тест уникального ограничения: категория с тем же именем для того же типа."""
        with self.assertRaises(IntegrityError):
            Category.objects.create(
                name='Продажи',
                slug='sales-duplicate',
                type=self.income_type
            )

    def test_unique_constraints_different_types(self):
        """Тест: категории с одинаковым именем разрешены для разных типов."""
        category_same_name = Category.objects.create(
            name='Продажи',
            slug='sales-expense',
            type=self.expense_type
        )
        self.assertIsNotNone(category_same_name)
        self.assertEqual(category_same_name.name, 'Продажи')
        self.assertEqual(category_same_name.type, self.expense_type)


class FormsTestCase(TestCase):
    """Тесты форм приложения."""

    def setUp(self):
        """Создание тестовых данных."""
        self.status = Status.objects.create(name='Бизнес', slug='business')
        self.income_type = Type.objects.create(name='Пополнение', slug='income')
        self.expense_type = Type.objects.create(name='Списание', slug='expense')

        self.income_category = Category.objects.create(
            name='Продажи', slug='sales', type=self.income_type
        )
        self.expense_category = Category.objects.create(
            name='Маркетинг', slug='marketing', type=self.expense_type
        )

        self.income_subcategory = Subcategory.objects.create(
            name='Онлайн продажи', slug='online-sales', category=self.income_category
        )
        self.expense_subcategory = Subcategory.objects.create(
            name='Avito', slug='avito', category=self.expense_category
        )

    def test_transaction_form_valid_data(self):
        """Тест валидной формы транзакции."""
        form_data = {
            'date': date.today(),
            'status': self.status.id,
            'type': self.income_type.id,
            'category': self.income_category.id,
            'subcategory': self.income_subcategory.id,
            'amount': '1000.00',
            'comment': 'Тестовая транзакция'
        }

        form = TransactionForm(data=form_data)
        self.assertTrue(form.is_valid(), f"Form errors: {form.errors}")

    def test_transaction_form_invalid_relationships(self):
        """Тест невалидной формы с нарушением иерархических зависимостей."""
        form_data = {
            'date': date.today(),
            'status': self.status.id,
            'type': self.income_type.id,
            'category': self.income_category.id,
            'subcategory': self.expense_subcategory.id,
            'amount': '1000.00'
        }

        form = TransactionForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('subcategory', form.errors)

    def test_transaction_form_missing_required_fields(self):
        """Тест формы с отсутствующими обязательными полями."""
        form_data = {
            'date': date.today(),
            'comment': 'Тест'
        }

        form = TransactionForm(data=form_data)
        self.assertFalse(form.is_valid())
        self.assertIn('status', form.errors)
        self.assertIn('type', form.errors)
        self.assertIn('category', form.errors)
        self.assertIn('subcategory', form.errors)
        self.assertIn('amount', form.errors)

    def test_transaction_filter_form(self):
        """Тест формы фильтрации транзакций."""
        form_data = {
            'date_from': date.today() - timedelta(days=30),
            'date_to': date.today(),
            'status': self.status.id,
            'type': self.income_type.id
        }

        form = TransactionFilterForm(data=form_data)
        self.assertTrue(form.is_valid())

    def test_transaction_form_with_editing_instance(self):
        """Тест формы при редактировании существующей транзакции."""
        transaction = Transaction.objects.create(
            date=date.today(),
            status=self.status,
            type=self.income_type,
            category=self.income_category,
            subcategory=self.income_subcategory,
            amount=Decimal('500.00')
        )

        form = TransactionForm(instance=transaction)
        self.assertEqual(
            form.fields['category'].queryset.count(),
            Category.objects.filter(type=self.income_type).count()
        )


class ViewsTestCase(TestCase):
    """Тесты представлений приложения."""

    def setUp(self):
        """Создание тестовых данных и HTTP-клиента."""
        self.client = Client()

        self.status = Status.objects.create(name='Бизнес', slug='business')
        self.income_type = Type.objects.create(name='Пополнение', slug='income')
        self.expense_type = Type.objects.create(name='Списание', slug='expense')

        self.income_category = Category.objects.create(
            name='Продажи', slug='sales', type=self.income_type
        )
        self.expense_category = Category.objects.create(
            name='Маркетинг', slug='marketing', type=self.expense_type
        )

        self.income_subcategory = Subcategory.objects.create(
            name='Онлайн продажи', slug='online-sales', category=self.income_category
        )
        self.expense_subcategory = Subcategory.objects.create(
            name='Avito', slug='avito', category=self.expense_category
        )

        self.transaction1 = Transaction.objects.create(
            date=date.today(),
            status=self.status,
            type=self.income_type,
            category=self.income_category,
            subcategory=self.income_subcategory,
            amount=Decimal('1000.00'),
            comment='Доход'
        )

        self.transaction2 = Transaction.objects.create(
            date=date.today() - timedelta(days=1),
            status=self.status,
            type=self.expense_type,
            category=self.expense_category,
            subcategory=self.expense_subcategory,
            amount=Decimal('500.00'),
            comment='Расход'
        )

    def test_transaction_list_view(self):
        """Тест отображения списка транзакций."""
        response = self.client.get(reverse('transaction_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Список транзакций')
        self.assertContains(response, '1')
        self.assertContains(response, '000')
        self.assertContains(response, '500')

    def test_transaction_list_filtering(self):
        """Тест фильтрации транзакций по типу."""
        response = self.client.get(reverse('transaction_list'), {
            'type': self.income_type.id
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, '1')
        self.assertContains(response, '000')
        self.assertEqual(len(response.context['transactions']), 1)
        self.assertEqual(response.context['transactions'][0].amount, Decimal('1000.00'))

    def test_transaction_create_view_get(self):
        """Тест GET-запроса страницы создания транзакции."""
        response = self.client.get(reverse('transaction_create'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Создание транзакции')

    def test_transaction_create_view_post_valid(self):
        """Тест создания транзакции через POST-запрос."""
        data = {
            'date': date.today(),
            'status': self.status.id,
            'type': self.income_type.id,
            'category': self.income_category.id,
            'subcategory': self.income_subcategory.id,
            'amount': '2000.00',
            'comment': 'Новая транзакция'
        }

        response = self.client.post(reverse('transaction_create'), data)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(
            Transaction.objects.filter(amount=Decimal('2000.00')).exists()
        )

    def test_transaction_create_view_post_invalid(self):
        """Тест создания транзакции с невалидными данными."""
        data = {
            'date': date.today(),
            'status': self.status.id,
            'type': self.income_type.id,
            'category': self.income_category.id,
            'subcategory': self.expense_subcategory.id,
            'amount': '2000.00'
        }

        response = self.client.post(reverse('transaction_create'), data)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            Transaction.objects.filter(amount=Decimal('2000.00')).exists()
        )

    def test_transaction_update_view(self):
        """Тест GET-запроса страницы редактирования транзакции."""
        response = self.client.get(
            reverse('transaction_update', args=[self.transaction1.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Редактирование транзакции')
        self.assertContains(response, '1000')

    def test_transaction_update_post(self):
        """Тест обновления транзакции через POST-запрос."""
        data = {
            'date': date.today(),
            'status': self.status.id,
            'type': self.income_type.id,
            'category': self.income_category.id,
            'subcategory': self.income_subcategory.id,
            'amount': '1500.00',
            'comment': 'Обновленная транзакция'
        }

        response = self.client.post(
            reverse('transaction_update', args=[self.transaction1.pk]),
            data
        )

        self.assertEqual(response.status_code, 302)
        self.transaction1.refresh_from_db()
        self.assertEqual(self.transaction1.amount, Decimal('1500.00'))

    def test_transaction_update_change_category(self):
        """Тест изменения категории и подкатегории при редактировании."""
        alt_category = Category.objects.create(
            name='Другая категория', slug='other', type=self.income_type
        )
        alt_subcategory = Subcategory.objects.create(
            name='Другая подкатегория', slug='other-sub', category=alt_category
        )

        data = {
            'date': date.today(),
            'status': self.status.id,
            'type': self.income_type.id,
            'category': alt_category.id,
            'subcategory': alt_subcategory.id,
            'amount': '1000.00',
            'comment': 'Изменены категории'
        }

        response = self.client.post(
            reverse('transaction_update', args=[self.transaction1.pk]),
            data
        )

        self.assertEqual(response.status_code, 302)
        self.transaction1.refresh_from_db()
        self.assertEqual(self.transaction1.category, alt_category)
        self.assertEqual(self.transaction1.subcategory, alt_subcategory)

    def test_transaction_delete_view(self):
        """Тест GET-запроса страницы подтверждения удаления."""
        response = self.client.get(
            reverse('transaction_delete', args=[self.transaction1.pk])
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Подтверждение удаления')

    def test_transaction_delete_post(self):
        """Тест удаления транзакции через POST-запрос."""
        transaction_id = self.transaction1.pk

        response = self.client.post(
            reverse('transaction_delete', args=[transaction_id])
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Transaction.objects.filter(pk=transaction_id).exists())

    def test_references_list_view(self):
        """Тест страницы управления справочниками."""
        response = self.client.get(reverse('references_list'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Управление справочниками')
        self.assertContains(response, 'Бизнес')
        self.assertContains(response, 'Пополнение')


class AjaxViewsTestCase(TestCase):
    """Тесты AJAX endpoints для динамической загрузки данных."""

    def setUp(self):
        """Создание тестовых данных."""
        self.client = Client()

        self.income_type = Type.objects.create(name='Пополнение', slug='income')
        self.expense_type = Type.objects.create(name='Списание', slug='expense')

        self.income_category = Category.objects.create(
            name='Продажи', slug='sales', type=self.income_type
        )
        self.expense_category = Category.objects.create(
            name='Маркетинг', slug='marketing', type=self.expense_type
        )

        self.income_subcategory = Subcategory.objects.create(
            name='Онлайн продажи', slug='online-sales', category=self.income_category
        )
        self.expense_subcategory = Subcategory.objects.create(
            name='Avito', slug='avito', category=self.expense_category
        )

    def test_load_categories_ajax(self):
        """Тест AJAX загрузки категорий по типу."""
        response = self.client.get(reverse('ajax_load_categories'), {
            'type_id': self.income_type.id
        })

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Продажи')
        self.assertEqual(data[0]['id'], self.income_category.id)

    def test_load_categories_ajax_invalid_type(self):
        """Тест AJAX загрузки категорий с несуществующим типом."""
        response = self.client.get(reverse('ajax_load_categories'), {
            'type_id': 999
        })

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data), 0)

    def test_load_subcategories_ajax(self):
        """Тест AJAX загрузки подкатегорий по категории."""
        response = self.client.get(reverse('ajax_load_subcategories'), {
            'category_id': self.income_category.id
        })

        self.assertEqual(response.status_code, 200)

        data = json.loads(response.content)
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]['name'], 'Онлайн продажи')
        self.assertEqual(data[0]['id'], self.income_subcategory.id)

    def test_load_subcategories_ajax_invalid_category(self):
        """Тест AJAX загрузки подкатегорий с несуществующей категорией."""
        response = self.client.get(reverse('ajax_load_subcategories'), {
            'category_id': 999
        })

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data), 0)


class ReferenceCRUDTestCase(TestCase):
    """Тесты базовых CRUD операций со справочниками."""

    def setUp(self):
        """Создание тестовых данных."""
        self.client = Client()

        self.status = Status.objects.create(name='Бизнес', slug='business')
        self.type = Type.objects.create(name='Пополнение', slug='income')

    def test_status_create(self):
        """Тест создания статуса."""
        data = {
            'name': 'Личное',
            'slug': 'personal'
        }

        response = self.client.post(reverse('status_create'), data)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Status.objects.filter(name='Личное').exists())

    def test_status_update(self):
        """Тест редактирования статуса."""
        data = {
            'name': 'Бизнес обновленный',
            'slug': 'business-updated'
        }

        response = self.client.post(
            reverse('status_update', kwargs={'slug': self.status.slug}),
            data
        )

        self.assertEqual(response.status_code, 302)
        self.status.refresh_from_db()
        self.assertEqual(self.status.name, 'Бизнес обновленный')

    def test_status_delete(self):
        """Тест удаления статуса."""
        status_slug = self.status.slug

        response = self.client.post(
            reverse('status_delete', kwargs={'slug': status_slug})
        )

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Status.objects.filter(slug=status_slug).exists())

    def test_category_create_with_type(self):
        """Тест создания категории с привязкой к типу."""
        data = {
            'name': 'Новая категория',
            'slug': 'new-category',
            'type': self.type.id
        }

        response = self.client.post(reverse('category_create'), data)

        self.assertEqual(response.status_code, 302)
        category = Category.objects.get(name='Новая категория')
        self.assertEqual(category.type, self.type)


class IntegrationTestCase(TestCase):
    """Интеграционные тесты полного цикла работы с данными."""

    def setUp(self):
        """Создание полного набора тестовых данных."""
        self.client = Client()

        self.status = Status.objects.create(name='Бизнес', slug='business')
        self.income_type = Type.objects.create(name='Пополнение', slug='income')
        self.expense_type = Type.objects.create(name='Списание', slug='expense')

        self.income_category = Category.objects.create(
            name='Продажи', slug='sales', type=self.income_type
        )
        self.expense_category = Category.objects.create(
            name='Маркетинг', slug='marketing', type=self.expense_type
        )

        self.income_subcategory = Subcategory.objects.create(
            name='Онлайн продажи', slug='online-sales', category=self.income_category
        )
        self.expense_subcategory = Subcategory.objects.create(
            name='Avito', slug='avito', category=self.expense_category
        )

    def test_full_transaction_workflow(self):
        """Тест полного цикла: создание → редактирование → отображение → удаление."""
        # Создание
        create_data = {
            'date': date.today(),
            'status': self.status.id,
            'type': self.income_type.id,
            'category': self.income_category.id,
            'subcategory': self.income_subcategory.id,
            'amount': '1000.00',
            'comment': 'Интеграционный тест'
        }

        response = self.client.post(reverse('transaction_create'), create_data)
        self.assertEqual(response.status_code, 302)

        transaction = Transaction.objects.get(comment='Интеграционный тест')
        self.assertEqual(transaction.amount, Decimal('1000.00'))

        # Редактирование
        update_data = create_data.copy()
        update_data['amount'] = '1500.00'
        update_data['comment'] = 'Обновленный тест'

        response = self.client.post(
            reverse('transaction_update', args=[transaction.pk]),
            update_data
        )
        self.assertEqual(response.status_code, 302)

        transaction.refresh_from_db()
        self.assertEqual(transaction.amount, Decimal('1500.00'))

        # Проверка в списке
        response = self.client.get(reverse('transaction_list'))
        self.assertContains(response, '1')
        self.assertContains(response, '500')

        # Удаление
        response = self.client.post(
            reverse('transaction_delete', args=[transaction.pk])
        )
        self.assertEqual(response.status_code, 302)

        self.assertFalse(
            Transaction.objects.filter(pk=transaction.pk).exists()
        )

    def test_cascading_dependency_workflow(self):
        """Тест каскадной загрузки зависимостей через AJAX."""
        # Загрузка категорий для типа
        response = self.client.get(reverse('ajax_load_categories'), {
            'type_id': self.income_type.id
        })

        categories = json.loads(response.content)
        self.assertEqual(len(categories), 1)
        self.assertEqual(categories[0]['id'], self.income_category.id)

        # Загрузка подкатегорий для категории
        response = self.client.get(reverse('ajax_load_subcategories'), {
            'category_id': self.income_category.id
        })

        subcategories = json.loads(response.content)
        self.assertEqual(len(subcategories), 1)
        self.assertEqual(subcategories[0]['id'], self.income_subcategory.id)

        # Создание транзакции с этими зависимостями
        data = {
            'date': date.today(),
            'status': self.status.id,
            'type': self.income_type.id,
            'category': self.income_category.id,
            'subcategory': self.income_subcategory.id,
            'amount': '1000.00'
        }

        response = self.client.post(reverse('transaction_create'), data)
        self.assertEqual(response.status_code, 302)

        transaction = Transaction.objects.latest('id')
        self.assertEqual(transaction.type, self.income_type)
        self.assertEqual(transaction.category, self.income_category)
        self.assertEqual(transaction.subcategory, self.income_subcategory)


class StatusCRUDTestCase(TestCase):
    """Детальные тесты CRUD операций со статусами."""

    def setUp(self):
        self.client = Client()
        self.status = Status.objects.create(name='Тестовый статус', slug='test-status')

    def test_status_create_get(self):
        """Тест GET-запроса формы создания статуса."""
        response = self.client.get(reverse('status_create'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Создание статуса')
        self.assertContains(response, 'Создать')

    def test_status_create_post_valid(self):
        """Тест создания статуса через POST-запрос."""
        data = {
            'name': 'Новый статус',
            'slug': 'new-status'
        }

        response = self.client.post(reverse('status_create'), data)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Status.objects.filter(name='Новый статус').exists())

        messages_list = list(response.wsgi_request._messages)
        self.assertTrue(any('успешно создан' in str(m) for m in messages_list))

    def test_status_update_get(self):
        """Тест GET-запроса формы редактирования статуса."""
        response = self.client.get(reverse('status_update', kwargs={'slug': self.status.slug}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'Редактирование статуса &quot;{self.status.name}&quot;')
        self.assertContains(response, 'Сохранить')

    def test_status_update_post_valid(self):
        """Тест обновления статуса через POST-запрос."""
        data = {
            'name': 'Обновленный статус',
            'slug': 'updated-status'
        }

        response = self.client.post(reverse('status_update', kwargs={'slug': self.status.slug}), data)

        self.assertEqual(response.status_code, 302)
        self.status.refresh_from_db()
        self.assertEqual(self.status.name, 'Обновленный статус')

    def test_status_delete_get(self):
        """Тест GET-запроса формы подтверждения удаления статуса."""
        response = self.client.get(reverse('status_delete', kwargs={'slug': self.status.slug}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'статус')

    def test_status_delete_post(self):
        """Тест удаления статуса через POST-запрос."""
        status_slug = self.status.slug

        response = self.client.post(reverse('status_delete', kwargs={'slug': status_slug}))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Status.objects.filter(slug=status_slug).exists())


class TypeCRUDTestCase(TestCase):
    """Детальные тесты CRUD операций с типами операций."""

    def setUp(self):
        self.client = Client()
        self.type = Type.objects.create(name='Тестовый тип', slug='test-type')

    def test_type_create_get(self):
        """Тест GET-запроса формы создания типа."""
        response = self.client.get(reverse('type_create'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Создание типа')

    def test_type_create_post_valid(self):
        """Тест создания типа через POST-запрос."""
        data = {
            'name': 'Новый тип',
            'slug': 'new-type'
        }

        response = self.client.post(reverse('type_create'), data)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Type.objects.filter(name='Новый тип').exists())

    def test_type_update_get(self):
        """Тест GET-запроса формы редактирования типа."""
        response = self.client.get(reverse('type_update', kwargs={'slug': self.type.slug}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'Редактирование типа &quot;{self.type.name}&quot;')

    def test_type_update_post_valid(self):
        """Тест обновления типа через POST-запрос."""
        data = {
            'name': 'Обновленный тип',
            'slug': 'updated-type'
        }

        response = self.client.post(reverse('type_update', kwargs={'slug': self.type.slug}), data)

        self.assertEqual(response.status_code, 302)
        self.type.refresh_from_db()
        self.assertEqual(self.type.name, 'Обновленный тип')

    def test_type_delete_post(self):
        """Тест удаления типа через POST-запрос."""
        type_slug = self.type.slug

        response = self.client.post(reverse('type_delete', kwargs={'slug': type_slug}))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Type.objects.filter(slug=type_slug).exists())


class CategoryCRUDTestCase(TestCase):
    """Детальные тесты CRUD операций с категориями."""

    def setUp(self):
        self.client = Client()
        self.type = Type.objects.create(name='Тестовый тип', slug='test-type')
        self.category = Category.objects.create(
            name='Тестовая категория',
            slug='test-category',
            type=self.type
        )

    def test_category_create_get(self):
        """Тест GET-запроса формы создания категории."""
        response = self.client.get(reverse('category_create'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Создание категории')

    def test_category_create_post_valid(self):
        """Тест создания категории через POST-запрос."""
        data = {
            'name': 'Новая категория',
            'slug': 'new-category',
            'type': self.type.id
        }

        response = self.client.post(reverse('category_create'), data)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Category.objects.filter(name='Новая категория').exists())

    def test_category_update_get(self):
        """Тест GET-запроса формы редактирования категории."""
        response = self.client.get(reverse('category_update', kwargs={'slug': self.category.slug}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'Редактирование категории &quot;{self.category.name}&quot;')

    def test_category_delete_post(self):
        """Тест удаления категории через POST-запрос."""
        category_slug = self.category.slug

        response = self.client.post(reverse('category_delete', kwargs={'slug': category_slug}))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Category.objects.filter(slug=category_slug).exists())


class SubcategoryCRUDTestCase(TestCase):
    """Детальные тесты CRUD операций с подкатегориями."""

    def setUp(self):
        self.client = Client()
        self.type = Type.objects.create(name='Тестовый тип', slug='test-type')
        self.category = Category.objects.create(
            name='Тестовая категория',
            slug='test-category',
            type=self.type
        )
        self.subcategory = Subcategory.objects.create(
            name='Тестовая подкатегория',
            slug='test-subcategory',
            category=self.category
        )

    def test_subcategory_create_get(self):
        """Тест GET-запроса формы создания подкатегории."""
        response = self.client.get(reverse('subcategory_create'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Создание подкатегории')

    def test_subcategory_create_post_valid(self):
        """Тест создания подкатегории через POST-запрос."""
        data = {
            'name': 'Новая подкатегория',
            'slug': 'new-subcategory',
            'category': self.category.id
        }

        response = self.client.post(reverse('subcategory_create'), data)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(Subcategory.objects.filter(name='Новая подкатегория').exists())

    def test_subcategory_update_get(self):
        """Тест GET-запроса формы редактирования подкатегории."""
        response = self.client.get(reverse('subcategory_update', kwargs={'slug': self.subcategory.slug}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f'Редактирование подкатегории &quot;{self.subcategory.name}&quot;')

    def test_subcategory_delete_post(self):
        """Тест удаления подкатегории через POST-запрос."""
        subcategory_slug = self.subcategory.slug

        response = self.client.post(reverse('subcategory_delete', kwargs={'slug': subcategory_slug}))

        self.assertEqual(response.status_code, 302)
        self.assertFalse(Subcategory.objects.filter(slug=subcategory_slug).exists())


class ErrorHandlingTestCase(TestCase):
    """Тесты обработки ошибок и граничных случаев."""

    def setUp(self):
        self.client = Client()

    def test_transaction_update_404(self):
        """Тест 404 при попытке редактирования несуществующей транзакции."""
        response = self.client.get(reverse('transaction_update', args=[999]))
        self.assertEqual(response.status_code, 404)

    def test_transaction_delete_404(self):
        """Тест 404 при попытке удаления несуществующей транзакции."""
        response = self.client.get(reverse('transaction_delete', args=[999]))
        self.assertEqual(response.status_code, 404)

    def test_status_update_404(self):
        """Тест 404 при попытке редактирования несуществующего статуса."""
        response = self.client.get(reverse('status_update', kwargs={'slug': 'nonexistent'}))
        self.assertEqual(response.status_code, 404)

    def test_ajax_load_categories_empty_type(self):
        """Тест AJAX загрузки категорий без параметра type_id."""
        response = self.client.get(reverse('ajax_load_categories'))

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data), 0)

    def test_ajax_load_subcategories_empty_category(self):
        """Тест AJAX загрузки подкатегорий без параметра category_id."""
        response = self.client.get(reverse('ajax_load_subcategories'))

        self.assertEqual(response.status_code, 200)
        data = json.loads(response.content)
        self.assertEqual(len(data), 0)
