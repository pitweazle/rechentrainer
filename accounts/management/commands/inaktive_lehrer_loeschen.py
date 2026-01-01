from datetime import timedelta
from pathlib import Path
import json

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User, Group
from django.conf import settings

from accounts.models import Profil, Geloescht
from core.models import Protokoll


COUNTER_FILE = Path(settings.BASE_DIR) / "core" / "zaehler_geloeschte_aufgaben.json"

if not COUNTER_FILE.exists():
    COUNTER_FILE.write_text(json.dumps({"anzahl": 0}))


def add_geloeschte_aufgaben(n: int):
    data = json.loads(COUNTER_FILE.read_text())
    data["anzahl"] += n
    COUNTER_FILE.write_text(json.dumps(data))


class Command(BaseCommand):
    help = "Löscht Lehrer, die >366 Tage inaktiv waren UND deren Lerngruppen auch >366 Tage inaktiv sind."

    def handle(self, *args, **options):
        grenze = timezone.now().date() - timedelta(days=366)

        try:
            gruppe_lehrer = Group.objects.get(name="Lehrer")
        except Group.DoesNotExist:
            self.stdout.write("WARNUNG: Gruppe 'Lehrer' existiert nicht.")
            return

        lehrer_qs = (
            User.objects
            .filter(groups=gruppe_lehrer, is_superuser=False, is_staff=False)
            .prefetch_related("lerngruppen")
        )

        geloeschte_lehrer = 0
        geloeschte_gruppen = 0
        gesamt_geloeschte_aufgaben = 0

        for lehrer in lehrer_qs:
            profil = Profil.objects.filter(user=lehrer).first()

            # letzte eigene Aufgabe des Lehrers
            letzte_lehrer = None
            if profil is not None:
                letzte_lehrer = (
                    Protokoll.objects
                    .filter(profil=profil)
                    .order_by("-start")
                    .first()
                )

            lehrer_aktiv = (
                letzte_lehrer is not None
                and letzte_lehrer.start.date() >= grenze
            )

            # Lerngruppen des Lehrers
            lerngruppen = list(lehrer.lerngruppen.all())
            anzahl_gruppen = len(lerngruppen)

            # letzte Aufgabe irgendeines Schülers in seinen Gruppen
            gruppen_profile = Profil.objects.filter(gruppe__in=lerngruppen)
            letzte_gruppe = (
                Protokoll.objects
                .filter(profil__in=gruppen_profile)
                .order_by("-start")
                .first()
            )

            gruppe_aktiv = (
                letzte_gruppe is not None
                and letzte_gruppe.start.date() >= grenze
            )

            # Wenn Lehrer ODER Gruppen innerhalb 366 Tage aktiv → NICHT löschen
            if lehrer_aktiv or gruppe_aktiv:
                continue

            # Ab hier: Lehrer + Gruppen wirklich inaktiv → löschen

            qs_protokolle = Protokoll.objects.filter(
                profil__in=list(gruppen_profile) + ([profil] if profil else [])
            )
            anzahl_aufgaben = qs_protokolle.count()

            gesamt_geloeschte_aufgaben += anzahl_aufgaben
            add_geloeschte_aufgaben(anzahl_aufgaben)
            qs_protokolle.delete()

            # Infos für Log
            name = f"{profil.vorname} {profil.nachname}" if profil else lehrer.username
            lehrer_datum = letzte_lehrer.start.date() if letzte_lehrer else None
            gruppe_datum = letzte_gruppe.start.date() if letzte_gruppe else None

            text = (
                f"Lehrer {name} ({lehrer.username}) wurde gelöscht. "
                f"Lerngruppen: {anzahl_gruppen}. "
                f"Letzte eigene Aufgabe: {lehrer_datum if lehrer_datum else 'nie'}. "
                f"Letzte Gruppenaufgabe: {gruppe_datum if gruppe_datum else 'nie'}. "
                f"Insgesamt {anzahl_aufgaben} Aufgaben gelöscht. "
                f"Grund: Inaktivität >366 Tage (Lehrer und Gruppen)."
            )

            Geloescht.objects.create(
                benutzername=lehrer.username,
                grund="lehrer_inaktiv_366_tage",
                text=text,
            )

            # Gruppen löschen
            geloeschte_gruppen += anzahl_gruppen
            for lg in lerngruppen:
                lg.delete()

            # Profil + User löschen
            if profil:
                profil.delete()
            lehrer.delete()

            geloeschte_lehrer += 1
            self.stdout.write(text)

        self.stdout.write("")
        self.stdout.write("-----------------------------------------------------")
        self.stdout.write(f"   Insgesamt gelöschte Lehrer:   {geloeschte_lehrer}")
        self.stdout.write(f"   Insgesamt gelöschte Gruppen:  {geloeschte_gruppen}")
        self.stdout.write(f"   Insgesamt gelöschte Aufgaben: {gesamt_geloeschte_aufgaben}")
        self.stdout.write("-----------------------------------------------------")
        self.stdout.write("")
