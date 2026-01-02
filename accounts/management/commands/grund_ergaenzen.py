from django.core.management.base import BaseCommand
from accounts.models import Geloescht


class Command(BaseCommand):
    help = "Setzt das Feld 'grund' anhand des Textes in Geloescht.text"

    def handle(self, *args, **options):
        aktualisiert = 0
        uebersprungen = 0

        for eintrag in Geloescht.objects.all():
            # Wenn schon etwas im Feld steht, lassen wir es in Ruhe
            if getattr(eintrag, "grund", None) is not None and eintrag.grund != "sonstiges":
                uebersprungen += 1
                continue
            text = eintrag.text or ""
            t = text.lower()
            grund = None
            # 1) Alte Tests: "älter als 1 Jahr" o.ä.
            if "test '" in text and "älter als" in t:
                grund = "alter_test"
            # 2) User ohne Profil / unvollständige Anmeldung
            elif "kein profil" in t or "unvollständige anmeldung" in t:
                grund = "user_ohne_profil"
            # 3) Schüler wegen Inaktivität (unsere Texte beginnen mit 'Schüler ...')
            elif t.startswith("schüler") and "inaktiv" in t:
                grund = "schueler_inaktiv"
            # 4) Lehrer wegen Inaktivität (unsere Texte beginnen mit 'Lehrer ...')
            elif t.startswith("lehrer") and "inaktiv" in t:
                grund = "lehrer_inaktiv"
            # 5) Zähler / Statistik gelöscht
            elif "das userprofil" in t :
                grund = "doppelter_account"
            elif "zähler" in t :
                grund = "zähler_verschoben"
            elif "aufgaben gelöscht" in t:
                grund = "aufgaben_geloescht"
            elif "zaehler angelegt" in t:
                grund = "zähler angelegt"
            elif "übertragen" in t:
                grund = "aufgaben_übertragen"
            # 7) Allgemeines Löschen von Aufgaben
            # Fallback
            if grund is None:
                grund = "sonstiges"

            eintrag.grund = grund
            eintrag.save(update_fields=["grund"])
            aktualisiert += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"{aktualisiert} Einträge aktualisiert, {uebersprungen} mit bestehendem Grund übersprungen."
            )
        )
