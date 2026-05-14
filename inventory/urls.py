from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('db-check/', views.db_check, name='db_check'),
    path('products/', views.product_list, name='product_list'),
    path('products/<slug:slug>/', views.product_detail, name='product_detail'),
]
