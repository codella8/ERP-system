# employee/urls.py
from django.urls import path
from . import views

app_name = 'employee'

urlpatterns = [
    path('', views.people_management, name='management'),
    path('list/', views.person_list, name='person_list'),
    path('detail/<uuid:pk>/', views.person_detail, name='person_detail'),
    path('delete/<uuid:pk>/', views.person_delete, name='person_delete'),
    
    path('api/person/create/', views.person_create_ajax, name='person_create_ajax'),
    path('api/person/<uuid:pk>/update/', views.person_update_ajax, name='person_update_ajax'),
    path('api/person/<uuid:pk>/get/', views.get_person_json, name='get_person_json'),

    path('api/transaction/<uuid:pk>/delete/', views.transaction_delete_ajax, name='transaction_delete_ajax'),

    path('api/transaction/create/', views.transaction_create_ajax, name='transaction_create_ajax'),
    path('api/transaction/<uuid:pk>/update/', views.transaction_update_ajax, name='transaction_update_ajax'),
    path('api/transaction/<uuid:pk>/delete/', views.transaction_delete_ajax, name='transaction_delete_ajax'),
]