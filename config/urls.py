from django.urls import URLPattern, URLResolver, path

from drlibre.interfaces.api import api

urlpatterns: list[URLPattern | URLResolver] = [
    path("api/v1/", api.urls),
]
