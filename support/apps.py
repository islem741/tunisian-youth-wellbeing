from django.apps import AppConfig


class SupportConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "support"

    def ready(self) -> None:
        import support.signals  # noqa: F401 — registers signal handlers
