from django.apps import AppConfig


class AuditConfig(AppConfig):
    name = "drlibre.audit.infrastructure.django"
    label = "audit"
    default_auto_field = "django.db.models.BigAutoField"
