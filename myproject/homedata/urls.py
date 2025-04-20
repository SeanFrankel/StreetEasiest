from django.urls import path
from .views import rental_data_json, rental_trends_json

app_name = 'homedata'

urlpatterns = [
    path('rental-data-json/', rental_data_json, name='rental_data_json'),
    path('rental-trends-json/', rental_trends_json, name='rental_trends_json'),
] 