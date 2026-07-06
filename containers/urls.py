from django.urls import path
from . import views

app_name = 'containers'

urlpatterns = [
    path('', views.container_list, name='list'),
    path('<uuid:pk>/', views.container_detail, name='detail'),
    path('inventory/', views.inventory_list, name='inventory_list'),
    path('payments/', views.payment_list, name='payment'),
    path('api/payment/<uuid:pk>/update/', views.payment_update_ajax, name='payment_update_ajax'),
    path('api/payment/<uuid:pk>/delete/', views.payment_delete_ajax, name='payment_delete_ajax'),
    path('api/payment/create/', views.payment_create_ajax, name='payment_create_ajax'),
    # API
    # containers/urls.py
    path('api/container/create/', views.container_create_ajax, name='container_create_ajax'),
    path('api/container/<uuid:pk>/update/', views.container_update_ajax, name='container_update_ajax'),
    path('api/container/<uuid:pk>/delete/', views.container_delete_ajax, name='container_delete_ajax'),
    path('api/inventory/create/', views.inventory_create_ajax, name='inventory_create_ajax'),
    path('api/inventory/create/', views.inventory_create_ajax, name='inventory_create_ajax'),
    path('api/inventory/<uuid:pk>/update/', views.inventory_update_ajax, name='inventory_update_ajax'),
    path('api/container/<uuid:pk>/get/', views.container_get_ajax, name='container_get_ajax'),
    path('api/inventory/<uuid:pk>/delete/', views.inventory_delete_ajax, name='inventory_delete_ajax'),
    # containers/urls.py
    path('api/expense/category/create/', views.expense_category_create_ajax, name='expense_category_create_ajax'),
    
    # containers/urls.py
    path('expenses/', views.expense_list, name='expense_list'),
    path('api/expense/create/', views.expense_create_ajax, name='expense_create_ajax'),
    path('api/expense/<uuid:pk>/update/', views.expense_update_ajax, name='expense_update_ajax'),
    path('api/expense/<uuid:pk>/delete/', views.expense_delete_ajax, name='expense_delete_ajax'),
    
    # Export
    path('export/containers/', views.export_containers_csv, name='export_containers_csv'),
    path('export/inventory/', views.export_inventory_csv, name='export_inventory_csv'),
]