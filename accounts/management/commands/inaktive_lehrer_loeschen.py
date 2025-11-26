from datetime import date, timedelta
from pathlib import Path
import json

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.contrib.auth.models import User, Group

from accounts.models import Profil, Lerngruppe, Geloescht
from core.models import Protokoll


# JSON-Zähler wie beim Schüler-Cleanup
COUNTER_FILE = (
    Path(__file__)
    .resolve()
    .parents[3]   # Projektroot
    / "core"
    / "zaehler_geloeschte_aufgaben.json"
)

if not COUNTER_FILE.exists():
    COUNTER_FILE.write_text(json.dumps({"anzahl": 0}))


def add_geloeschte_aufgaben(n: int):
    data = json.loads(COUNTER_FILE.read_text())
    data["anzahl"] += n
    COUNTER_FILE.write_text(json.dumps(data))


def schuljahr_grenzen():
    """Gibt Beginn aktuelles, letztes und vorletztes SJ zurück."""
    heute = timezone.now().date()
    jahr = heute.year
    beginn_sj = date(jahr, 8, 1)

    if heute < beginn_sj:
        beginn_aktuelles = date(jahr - 1, 8, 1)
    else:
        beginn_aktuelles = date(jahr, 8, 1)

    beginn_letztes = date(beginn_aktuelles.year - 1, 8, 1)
    beginn_vorletztes = date(beginn_aktuelles.year - 2, 8, 1)

    return beginn_aktuelles, beginn_letztes, beginn_vorletztes


class Command(BaseCommand):
    help = "Löscht Lehrer, die in zwei Schuljahren inaktiv waren und deren Lerngruppen auch inaktiv sind."

    def handle(self, *args, **options):
        beginn_aktuelles, beginn_letztes, beginn_vorletztes = schuljahr_grenzen()

        try:
            gruppe_lehrer = Group.objects.get(name="Lehrer")
        except Group.DoesNotExist:
            self.stdout.write("WARNUNG: Gruppe 'Lehrer' existiert nicht.")
            return

        # Nur echte Lehrer-User (keine Superuser/Staff)
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
                and letzte_lehrer.start.date() >= beginn_vorletztes
            )

            # alle Lerngruppen des Lehrers
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
                and letzte_gruppe.start.date() >= beginn_vorletztes
            )

            # Wenn Lehrer oder Gruppe in den letzten 2 SJ aktiv → NICHT löschen
            if lehrer_aktiv or gruppe_aktiv:
                continue

            # Ab hier: Lehrer + seine Gruppen wirklich komplett inaktiv → löschen

            # Alle Protokolle des Lehrers + seiner Gruppen löschen und zählen
            qs_protokolle = Protokoll.objects.filter(
                profil__in=list(gruppen_profile) + ([profil] if profil else [])
            )
            anzahl_aufgaben = qs_protokolle.count()
            gesamt_geloeschte_aufgaben += anzahl_aufgaben
            add_geloeschte_aufgaben(anzahl_aufgaben)
            qs_protokolle.delete()

            # Infos für Log
            if profil:
                name = f"{profil.vorname} {profil.nachname}"
            else:
                name = lehrer.username

            if letzte_lehrer:
                lehrer_datum = letzte_lehrer.start.date()
            else:
                lehrer_datum = None

            if letzte_gruppe:
                gruppe_datum = letzte_gruppe.start.date()
            else:
                gruppe_datum = None

            text = (
                f"Lehrer {name} ({lehrer.username}) wurde gelöscht. "
                f"Lerngruppen: {anzahl_gruppen}. "
                f"Letzte eigene Aufgabe: {lehrer_datum if lehrer_datum else 'nie'}. "
                f"Letzte Gruppenaufgabe: {gruppe_datum if gruppe_datum else 'nie'}. "
                f"Insgesamt {anzahl_aufgaben} Aufgaben gelöscht. "
                f"Grund: Inaktivität in zwei aufeinanderfolgenden Schuljahren."
            )

            Geloescht.objects.create(
                benutzername=lehrer.username,
                text=text,
            )

            # Lerngruppen explizit löschen (würden beim User-Delete per CASCADE auch wegfallen)
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
