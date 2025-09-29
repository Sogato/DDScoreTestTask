from django.urls import path
from . import views

urlpatterns = [
    # Главная страница со списком транзакций
    path('', views.transaction_list, name='transaction_list'),

    # Транзакции CRUD
    path('transaction/create/', views.transaction_create, name='transaction_create'),
    path('transaction/<int:pk>/edit/', views.transaction_update, name='transaction_update'),
    path('transaction/<int:pk>/delete/', views.transaction_delete, name='transaction_delete'),

    # AJAX для зависимых селектов
    path('ajax/load-categories/', views.load_categories, name='ajax_load_categories'),
    path('ajax/load-subcategories/', views.load_subcategories, name='ajax_load_subcategories'),

    # Управление справочниками
    path('references/', views.references_list, name='references_list'),

    # Status CRUD
    path('references/status/create/', views.StatusCreateView.as_view(), name='status_create'),
    path('references/status/<int:pk>/edit/', views.StatusUpdateView.as_view(), name='status_update'),
    path('references/status/<int:pk>/delete/', views.StatusDeleteView.as_view(), name='status_delete'),

    # Type CRUD
    path('references/type/create/', views.TypeCreateView.as_view(), name='type_create'),
    path('references/type/<int:pk>/edit/', views.TypeUpdateView.as_view(), name='type_update'),
    path('references/type/<int:pk>/delete/', views.TypeDeleteView.as_view(), name='type_delete'),

    # Category CRUD
    path('references/category/create/', views.CategoryCreateView.as_view(), name='category_create'),
    path('references/category/<int:pk>/edit/', views.CategoryUpdateView.as_view(), name='category_update'),
    path('references/category/<int:pk>/delete/', views.CategoryDeleteView.as_view(), name='category_delete'),

    # Subcategory CRUD
    path('references/subcategory/create/', views.SubcategoryCreateView.as_view(), name='subcategory_create'),
    path('references/subcategory/<int:pk>/edit/', views.SubcategoryUpdateView.as_view(), name='subcategory_update'),
    path('references/subcategory/<int:pk>/delete/', views.SubcategoryDeleteView.as_view(), name='subcategory_delete'),
]