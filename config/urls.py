from django.conf import settings
from django.urls import URLPattern, URLResolver, include, path, re_path
from django.views.static import serve

from drlibre.interfaces import fhir
from drlibre.interfaces.api import api

urlpatterns: list[URLPattern | URLResolver] = [
    path("api/v1/", api.urls),
    path("fhir/", fhir.urls()),
    path("", include("drlibre.interfaces.web.urls")),
    # Localhost has no static server in front of gunicorn, so Django serves the vendored files.
    re_path(r"^static/(?P<path>.*)$", serve, {"document_root": settings.STATICFILES_DIRS[0]}),
]

handler403 = "drlibre.interfaces.web.views.errors.forbidden"
handler404 = "drlibre.interfaces.web.views.errors.not_found"
