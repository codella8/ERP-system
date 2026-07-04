# daily_sale/urls.py
from django.urls import path
from . import views

app_name = "daily_sale"

urlpatterns = [
    path("create/", views.transaction_create, name="transaction_create"),
    path("", views.transaction_list, name="transaction_list"), 
    path("transactions/", views.transaction_list, name="transaction_list_alt"),
    path("daily-summary/", views.daily_summary, name="daily_summary"),
    

    path("transaction/<uuid:pk>/", views.invoice_view, name="invoice"),
    path('api/transaction/<uuid:pk>/update/', views.transaction_update_ajax, name='transaction_update_ajax'),
    path("transaction/<uuid:pk>/delete/", views.transaction_delete, name="transaction_delete"),
    
    path("ajax/create/", views.transaction_create_ajax, name="transaction_create_ajax"),
    path("ajax/item-details/", views.get_item_details, name="get_item_details"),
    path("ajax/search-items/", views.search_items, name="search_items"),
    path('ajax/search-container/', views.search_container, name='search_container'),

    path("api/summary/", views.daily_summary, name="api_summary"),
]