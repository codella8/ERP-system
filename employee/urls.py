from django.urls import path
from . import views

app_name = 'employee'

urlpatterns = [
    path('list/', views.person_list, name='person_list'),
    path('<uuid:pk>/', views.person_detail, name='employee_detail'),
]
