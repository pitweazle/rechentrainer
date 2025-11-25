from django.apps import AppConfig

# mathetests/apps.py
from django.apps import AppConfig

class MathetestsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mathetests"      # 👈 NEU: Importpfad der App (Ordnername)
    label = "tests"          # 👈 optional: alter App-Label behalten, damit Migrationen weiter passen
    verbose_name = "mathetests"


