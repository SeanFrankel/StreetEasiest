# homedata/urls.py
from django.urls import path
from .views import rental_data_json

urlpatterns = [
    path('rental-data-json/', rental_data_json, name='rental_data_json'),
]
