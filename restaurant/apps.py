from django.apps import AppConfig


class RestaurantConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "restaurant"

    def ready(self):
        # Registering signals here guarantees they are connected after the
        # application registry is fully initialized.
        from . import signals  # noqa: F401
