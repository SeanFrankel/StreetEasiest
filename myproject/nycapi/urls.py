# myproject/nycapi/urls.py
from django.urls import path
from .views import building_lookup_view

urlpatterns = [
    path("nyc-lookup-tool/", building_lookup_view, name="address_lookup"),
]
