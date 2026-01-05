# mathetests/management/commands/cleanup_old_tests.py

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from mathetests.models import Test
from accounts.models import Geloescht


class Command(BaseCommand):
    help = "Löscht Tests, die älter als 1 Jahr sind, und protokolliert das in Geloescht."

    def handle(self, *args, **options):
        grenze = timezone.now() - timedelta(days=366)
        alte_tests = Test.objects.filter(created_at__lte=grenze)

        if not alte_tests.exists():
            self.stdout.write("Keine alten Tests gefunden.")
            return

        for test in alte_tests:
            lehrer = getattr(test.gruppe, "lehrer", None)
            benutzername = lehrer.username if lehrer else ""
            text = f"Test '{test.name}' aus Gruppe '{test.gruppe.name}' gelöscht (älter als 1 Jahr)."
            Geloescht.objects.create(
                benutzername="cronjob",
                grund = "Test älter als ein Jahr",
                text=text,
            )
            test.delete()
            self.stdout.write(f"Gelöscht: {text}")
