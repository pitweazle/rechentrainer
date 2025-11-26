import re
from datetime import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from accounts.models import Geloescht

DATE_RE = re.compile(r"\d{4}-\d{2}-\d{2}")  # YYYY-MM-DD

class Command(BaseCommand):
    help = "Liest Datumsangaben aus Geloescht.text und trägt sie in erstellt_am ein"
    def handle(self, *args, **options):
        qs = Geloescht.objects.all()
        ok = 0
        none = 0
        for eintrag in qs:
            dates = DATE_RE.findall(eintrag.text)
            if not dates:
                none += 1
                continue  # lässt den bisherigen Timestamp unverändert
            # Wenn mehrere Datumsangaben: nimm die LETZTE
            datum_str = dates[-1]
            datum = datetime.fromisoformat(datum_str)
            if timezone.is_naive(datum):
                datum = timezone.make_aware(datum, timezone.get_default_timezone())
            eintrag.erstellt_am = datum
            eintrag.save(update_fields=["erstellt_am"])
            ok += 1
        self.stdout.write(f"{ok} Einträge aktualisiert, {none} ohne Datum belassen.")
