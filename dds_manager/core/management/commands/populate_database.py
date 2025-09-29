import random
from datetime import date, timedelta
from decimal import Decimal
from django.core.management.base import BaseCommand, CommandError
from django.utils.text import slugify
from django.db.models import Count, Sum
from unidecode import unidecode

from core.models import Status, Type, Category, Subcategory, Transaction

# ============================================================================
# КОНСТАНТЫ ДЛЯ НАСТРОЙКИ
# ============================================================================

# Параметры создания данных
DEFAULT_TRANSACTIONS_COUNT = 200 # Количество транзакций
TRANSACTIONS_DATE_RANGE_DAYS = 365  # За какой период создавать транзакции

# Распределение типов транзакций (в процентах)
INCOME_PERCENTAGE = 30  # Процент доходных операций
EXPENSE_PERCENTAGE = 70  # Процент расходных операций

# Вероятность создания пустого комментария (в долях от 0 до 1)
EMPTY_COMMENT_PROBABILITY = 0.2

# Частота вывода прогресса (каждые N транзакций)
PROGRESS_REPORT_INTERVAL = 50

# Диапазоны сумм для разных типов операций (в рублях)
AMOUNT_RANGES = {
    'Зарплата': (45000, 85000),
    'Премия': (10000, 50000),
    'Фриланс': (5000, 35000),
    'Дивиденды': (500, 15000),
    'Продукты': (500, 8000),
    'Транспорт': (200, 3000),
    'Аренда': (15000, 45000),
    'Развлечения': (500, 10000),
    'default': (100, 5000)
}

# Шаблоны комментариев
INCOME_COMMENT_TEMPLATES = [
    'Основной источник дохода',
    'Дополнительный заработок',
    'Премиальные выплаты',
    'Пассивный доход',
    'Продажа ненужных вещей',
    'Возврат долга',
    'Подарок на праздник',
    'Кэшбэк с покупок',
    'Выигрыш в лотерею',
    'Возврат переплаты'
]

EXPENSE_COMMENT_TEMPLATES = [
    'Закупка продуктов на неделю',
    'Оплата счетов',
    'Покупка необходимых вещей',
    'Развлечения с семьей',
    'Инвестиции в здоровье',
    'Образовательные расходы',
    'Поездка в {place}',
    'Подарок',
    'Техническое обслуживание',
    'Экстренные расходы'
]

# Данные для генерации комментариев
PLACES = ['Москву', 'Новосибирск', 'Санкт-Петербург', 'Екатеринбург', 'Краснодар', 'Сочи']

# Справочные данные
STATUS_NAMES = [
    'Бизнес',
    'Личное',
    'Налоги',
    'Инвестиции',
    'Благотворительность'
]

TYPE_NAMES = {
    'income': 'Пополнение',
    'expense': 'Списание'
}

# Категории для доходов
INCOME_CATEGORIES = [
    'Основная работа',
    'Фриланс и подработки',
    'Продажи товаров',
    'Инвестиционный доход',
    'Возврат долгов',
    'Подарки и премии'
]

# Категории для расходов
EXPENSE_CATEGORIES = [
    'Продукты питания',
    'Транспорт',
    'Жилье и коммунальные услуги',
    'Развлечения и отдых',
    'Образование и развитие',
    'Здоровье и медицина'
]

# Подкатегории для каждой категории
SUBCATEGORIES = {
    'Основная работа': ['Зарплата', 'Премия', 'Тринадцатая зарплата'],
    'Фриланс и подработки': ['Веб-разработка', 'Дизайн', 'Консультации'],
    'Продажи товаров': ['Авито', 'Wildberries', 'Личные продажи'],
    'Инвестиционный доход': ['Дивиденды', 'Проценты по депозитам', 'Прибыль от криптовалют'],
    'Возврат долгов': ['От друзей', 'Возврат займов', 'Страховые выплаты'],
    'Подарки и премии': ['День рождения', 'Новый год', 'Бонусы от работы'],
    'Продукты питания': ['Супермаркеты', 'Рестораны и кафе', 'Доставка еды'],
    'Транспорт': ['Общественный транспорт', 'Такси', 'Топливо'],
    'Жилье и коммунальные услуги': ['Аренда жилья', 'Электричество', 'Интернет и связь'],
    'Развлечения и отдых': ['Кино и театр', 'Спорт и фитнес', 'Путешествия'],
    'Образование и развитие': ['Курсы и тренинги', 'Книги', 'Программное обеспечение'],
    'Здоровье и медицина': ['Врачи и анализы', 'Лекарства', 'Спортивное питание']
}

# Маппинг категорий на статусы с весами (вероятностями)
# Формат: 'Категория': {'Статус': вес, ...}
# Чем больше вес, тем чаще категория будет в этом статусе
CATEGORY_STATUS_MAPPING = {
    # ДОХОДЫ
    'Основная работа': {
        'Бизнес': 60,
        'Личное': 40,
    },
    'Фриланс и подработки': {
        'Бизнес': 70,
        'Личное': 30,
    },
    'Продажи товаров': {
        'Бизнес': 80,
        'Личное': 20,
    },
    'Инвестиционный доход': {
        'Инвестиции': 90,
        'Личное': 10,
    },
    'Возврат долгов': {
        'Личное': 70,
        'Бизнес': 30,
    },
    'Подарки и премии': {
        'Личное': 80,
        'Бизнес': 20,
    },

    # РАСХОДЫ
    'Продукты питания': {
        'Личное': 90,
        'Бизнес': 10,
    },
    'Транспорт': {
        'Личное': 60,
        'Бизнес': 40,
    },
    'Жилье и коммунальные услуги': {
        'Личное': 70,
        'Бизнес': 20,
        'Налоги': 10,
    },
    'Развлечения и отдых': {
        'Личное': 85,
        'Бизнес': 10,
        'Благотворительность': 5,
    },
    'Образование и развитие': {
        'Бизнес': 50,
        'Личное': 40,
        'Инвестиции': 10,
    },
    'Здоровье и медицина': {
        'Личное': 90,
        'Бизнес': 10,
    },
}

# ============================================================================
# КОМАНДА
# ============================================================================

class Command(BaseCommand):
    """
    Команда для заполнения базы данных тестовыми данными ДДС-менеджера.

    Создает:
    - 5 статусов
    - 2 типа операций
    - 12 категорий (6 для доходов, 6 для расходов)
    - 36 подкатегорий (по 3 для каждой категории)
    - 75 транзакций за последний год (по умолчанию)

    Статусы распределяются реалистично на основе категорий:
    - Бизнес-категории чаще получают статус "Бизнес"
    - Инвестиционный доход → статус "Инвестиции"
    - Личные расходы → статус "Личное"
    - И т.д.
    """
    help = 'Заполняет базу данных тестовыми данными для ДДС-менеджера'

    def add_arguments(self, parser):
        parser.add_argument(
            '--transactions',
            type=int,
            default=DEFAULT_TRANSACTIONS_COUNT,
            help=f'Количество транзакций для создания (по умолчанию: {DEFAULT_TRANSACTIONS_COUNT})'
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Очистить существующие данные перед созданием новых'
        )

    def handle(self, **options):
        """Основной метод команды: выполняет заполнение базы данных."""

        if options['clear']:
            self._clear_data()

        # Создаем справочники
        statuses = self._create_statuses()
        types = self._create_types()
        categories = self._create_categories(types)
        subcategories = self._create_subcategories(categories)

        # Создаем транзакции
        transactions_count = options['transactions']
        self._create_transactions(statuses, types, subcategories, transactions_count)

        self.stdout.write(
            self.style.SUCCESS(f'База данных успешно заполнена тестовыми данными!')
        )
        self._print_statistics()

    def _clear_data(self):
        """Очищает существующие данные."""
        Transaction.objects.all().delete()
        Subcategory.objects.all().delete()
        Category.objects.all().delete()
        Type.objects.all().delete()
        Status.objects.all().delete()
        self.stdout.write(self.style.WARNING('Существующие данные очищены'))

    def _create_statuses(self):
        """Создает статусы операций."""
        statuses = []
        for name in STATUS_NAMES:
            status, created = Status.objects.get_or_create(
                name=name,
                defaults={'slug': slugify(unidecode(name))}
            )
            if created:
                self.stdout.write(f'  Создан статус: {name}')
            statuses.append(status)

        self.stdout.write(self.style.SUCCESS(f'Статусы: {len(statuses)} шт.'))
        return statuses

    def _create_types(self):
        """Создает типы операций и возвращает их в виде словаря."""
        types_dict = {}

        for key, name in TYPE_NAMES.items():
            type_obj, created = Type.objects.get_or_create(
                name=name,
                defaults={'slug': slugify(unidecode(name))}
            )
            if created:
                self.stdout.write(f'  Создан тип: {name}')
            types_dict[key] = type_obj

        self.stdout.write(self.style.SUCCESS(f'Типы: {len(types_dict)} шт.'))
        return types_dict

    def _create_categories(self, types):
        """Создает категории для каждого типа."""
        # Безопасный доступ к типам
        income_type = types.get('income')
        expense_type = types.get('expense')

        if not income_type or not expense_type:
            raise CommandError('Не удалось найти необходимые типы операций')

        categories = []

        # Создаем категории доходов
        for name in INCOME_CATEGORIES:
            category, created = Category.objects.get_or_create(
                name=name,
                type=income_type,
                defaults={'slug': slugify(unidecode(name))}
            )
            if created:
                self.stdout.write(f'  Создана категория доходов: {name}')
            categories.append(category)

        # Создаем категории расходов
        for name in EXPENSE_CATEGORIES:
            category, created = Category.objects.get_or_create(
                name=name,
                type=expense_type,
                defaults={'slug': slugify(unidecode(name))}
            )
            if created:
                self.stdout.write(f'  Создана категория расходов: {name}')
            categories.append(category)

        self.stdout.write(self.style.SUCCESS(f'Категории: {len(categories)} шт.'))
        return categories

    def _create_subcategories(self, categories):
        """Создает подкатегории для каждой категории."""
        subcategories = []

        for category in categories:
            if category.name in SUBCATEGORIES:
                for subcategory_name in SUBCATEGORIES[category.name]:
                    subcategory, created = Subcategory.objects.get_or_create(
                        name=subcategory_name,
                        category=category,
                        defaults={'slug': slugify(unidecode(subcategory_name))}
                    )
                    if created:
                        self.stdout.write(f'    Создана подкатегория: {subcategory_name} -> {category.name}')
                    subcategories.append(subcategory)

        self.stdout.write(self.style.SUCCESS(f'Подкатегории: {len(subcategories)} шт.'))
        return subcategories

    def _create_transactions(self, statuses, types, subcategories, count):
        """Создает транзакции."""
        income_type = types.get('income')
        expense_type = types.get('expense')

        if not income_type or not expense_type:
            raise CommandError('Не удалось найти необходимые типы операций')

        # Получаем подкатегории по типам
        income_subcategories = [s for s in subcategories if s.category.type == income_type]
        expense_subcategories = [s for s in subcategories if s.category.type == expense_type]

        if not income_subcategories or not expense_subcategories:
            raise CommandError('Недостаточно подкатегорий для создания транзакций')

        # Создаем словарь статусов для быстрого доступа по имени
        statuses_dict = {status.name: status for status in statuses}

        transactions_created = 0

        # Создаем транзакции за последний год
        start_date = date.today() - timedelta(days=TRANSACTIONS_DATE_RANGE_DAYS)

        for i in range(count):
            # Случайная дата в течение года
            random_days = random.randint(0, TRANSACTIONS_DATE_RANGE_DAYS)
            transaction_date = start_date + timedelta(days=random_days)

            # Определяем тип операции на основе заданных процентов
            is_income = random.choice(
                [True] * INCOME_PERCENTAGE + [False] * EXPENSE_PERCENTAGE
            )

            if is_income:
                transaction_type = income_type
                available_subcategories = income_subcategories
                comment_templates = INCOME_COMMENT_TEMPLATES
            else:
                transaction_type = expense_type
                available_subcategories = expense_subcategories
                comment_templates = EXPENSE_COMMENT_TEMPLATES

            # Выбираем случайную подкатегорию
            subcategory = random.choice(available_subcategories)
            category = subcategory.category

            # Определяем сумму на основе типа операции
            amount = self._generate_amount(subcategory.name)

            # Генерируем комментарий
            comment = self._generate_comment(comment_templates)

            # Выбираем статус на основе категории (weighted choice)
            status = self._get_status_for_category(category.name, statuses_dict)

            # Создаем транзакцию
            Transaction.objects.create(
                date=transaction_date,
                status=status,
                type=transaction_type,
                category=category,
                subcategory=subcategory,
                amount=amount,
                comment=comment
            )

            transactions_created += 1

            # Показываем прогресс
            if transactions_created % PROGRESS_REPORT_INTERVAL == 0:
                self.stdout.write(f'  Создано транзакций: {transactions_created}')

        self.stdout.write(
            self.style.SUCCESS(f'Транзакции: {transactions_created} шт.')
        )

    def _generate_amount(self, subcategory_name):
        """Генерирует сумму транзакции на основе типа подкатегории."""
        subcategory_lower = subcategory_name.lower()

        # Определяем диапазон суммы на основе ключевых слов
        if 'зарплата' in subcategory_lower:
            amount_range = AMOUNT_RANGES['Зарплата']
        elif 'премия' in subcategory_lower:
            amount_range = AMOUNT_RANGES['Премия']
        elif any(word in subcategory_lower for word in ['фриланс', 'разработка', 'дизайн']):
            amount_range = AMOUNT_RANGES['Фриланс']
        elif any(word in subcategory_lower for word in ['дивиденды', 'проценты', 'депозит']):
            amount_range = AMOUNT_RANGES['Дивиденды']
        elif any(word in subcategory_lower for word in ['продукты', 'супермаркет', 'еда']):
            amount_range = AMOUNT_RANGES['Продукты']
        elif any(word in subcategory_lower for word in ['транспорт', 'такси', 'топливо']):
            amount_range = AMOUNT_RANGES['Транспорт']
        elif any(word in subcategory_lower for word in ['аренда', 'жилье']):
            amount_range = AMOUNT_RANGES['Аренда']
        elif any(word in subcategory_lower for word in ['развлечения', 'кино', 'театр']):
            amount_range = AMOUNT_RANGES['Развлечения']
        else:
            amount_range = AMOUNT_RANGES['default']

        return Decimal(str(random.randint(amount_range[0], amount_range[1])))

    def _generate_comment(self, comment_templates):
        """Генерирует комментарий к транзакции."""
        # Иногда оставляем комментарий пустым
        if random.random() < EMPTY_COMMENT_PROBABILITY:
            return ''

        comment_template = random.choice(comment_templates)
        return comment_template.format(
            place=random.choice(PLACES)
        )

    def _get_status_for_category(self, category_name, statuses_dict):
        """
        Выбирает статус для категории на основе весов из маппинга.
        Использует weighted random choice для реалистичного распределения.
        """
        # Получаем маппинг весов для данной категории
        status_weights = CATEGORY_STATUS_MAPPING.get(category_name, {})

        # Если маппинг не найден, используем равномерное распределение
        if not status_weights:
            return random.choice(list(statuses_dict.values()))

        # Формируем списки статусов и их весов
        available_statuses = []
        weights = []

        for status_name, weight in status_weights.items():
            if status_name in statuses_dict:
                available_statuses.append(statuses_dict[status_name])
                weights.append(weight)

        # Выбираем статус с учетом весов
        if available_statuses:
            return random.choices(available_statuses, weights=weights, k=1)[0]
        else:
            # Фолбэк на случайный статус, если что-то пошло не так
            return random.choice(list(statuses_dict.values()))

    def _print_statistics(self):
        """Выводит статистику созданных данных."""
        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('СТАТИСТИКА СОЗДАННЫХ ДАННЫХ:'))
        self.stdout.write('=' * 50)

        # Общая статистика
        self.stdout.write(f'Статусы: {Status.objects.count()}')
        self.stdout.write(f'Типы: {Type.objects.count()}')
        self.stdout.write(f'Категории: {Category.objects.count()}')
        self.stdout.write(f'Подкатегории: {Subcategory.objects.count()}')
        self.stdout.write(f'Транзакции: {Transaction.objects.count()}')

        # Статистика по типам транзакций
        income_count = Transaction.objects.filter(type__name=TYPE_NAMES['income']).count()
        expense_count = Transaction.objects.filter(type__name=TYPE_NAMES['expense']).count()

        self.stdout.write(f'\nТранзакции по типам:')
        self.stdout.write(f'  Пополнения: {income_count}')
        self.stdout.write(f'  Списания: {expense_count}')

        # Суммы
        total_income = Transaction.objects.filter(type__name=TYPE_NAMES['income']).aggregate(
            total=Sum('amount')
        )['total'] or 0
        total_expense = Transaction.objects.filter(type__name=TYPE_NAMES['expense']).aggregate(
            total=Sum('amount')
        )['total'] or 0

        self.stdout.write(f'\nСуммы:')
        self.stdout.write(f'  Общий доход: {total_income:,.2f} ₽')
        self.stdout.write(f'  Общий расход: {total_expense:,.2f} ₽')
        self.stdout.write(f'  Баланс: {total_income - total_expense:,.2f} ₽')

        # Топ-5 категорий по количеству транзакций
        top_categories = Category.objects.annotate(
            transaction_count=Count('transactions')
        ).order_by('-transaction_count')[:5]

        self.stdout.write(f'\nТоп-5 категорий по активности:')
        for i, category in enumerate(top_categories, 1):
            self.stdout.write(f'  {i}. {category.name}: {category.transaction_count} транзакций')

        self.stdout.write('\n' + '=' * 50)
        self.stdout.write(self.style.SUCCESS('Готово! Можете тестировать приложение.'))
        self.stdout.write('=' * 50)
