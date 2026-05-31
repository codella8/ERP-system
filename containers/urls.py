# containers/urls.py
from django.urls import path
from . import views

app_name = 'containers'

urlpatterns = [
    # Container URLs
    path('', views.container_list, name='list'),
    path('<uuid:pk>/', views.container_detail, name='detail'),
    
    # Inventory URLs
    path('inventory/', views.inventory_list, name='inventory_list'),
    path('inventory/<uuid:pk>/', views.inventory_detail, name='inventory_detail'),
    
    # Report URLs
    path('reports/daily/', views.container_daily_report, name='daily_report'),
    path('reports/monthly/', views.container_monthly_summary, name='monthly_report'),
    
    # AJAX URLs
    path('api/container/create/', views.container_create_ajax, name='container_create_ajax'),
    path('api/container/<uuid:pk>/update/', views.container_update_ajax, name='container_update_ajax'),
    
    path('api/inventory/create/', views.inventory_create_ajax, name='inventory_create_ajax'),
    path('api/inventory/<uuid:pk>/update/', views.inventory_update_ajax, name='inventory_update_ajax'),
    path('api/inventory/<uuid:pk>/sell/', views.inventory_sell_ajax, name='inventory_sell_ajax'),
]