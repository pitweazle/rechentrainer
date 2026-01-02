from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from accounts.models import Geloescht

heute = timezone.now().date()

class Command(BaseCommand):
    help = "Löscht Geloescht-Einträge, die älter als 1 Jahr sind"

    def handle(self, *args, **options):
        grenze = timezone.now() - timedelta(days=365)
        alte = Geloescht.objects.filter(erstellt_am__lt=grenze)
        anzahl = alte.count()
        alte.delete()
        self.stdout.write(f"{anzahl} alte Geloescht-Einträge gelöscht.")

        Geloescht.objects.create(
            benutzername="cronjob",
            grund="cronjob",
            text=(f"{heute} {anzahl} alte Geloescht-Einträge gelöscht."),)
        