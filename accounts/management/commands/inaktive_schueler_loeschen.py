from datetime import timedelta, date

from django.utils import timezone
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group

from accounts.models import Profil, Geloescht
from core.models import Protokoll

import json
from pathlib import Path

heute = timezone.now().date()

# Beginn dieses Schuljahres bestimmen
jahr = heute.year
beginn_sj = date(jahr, 8, 1)

# Schuljahr läuft bis 31. Juli
if heute < beginn_sj:
    beginn_aktuelles_sj = date(jahr - 1, 8, 1)
else:
    beginn_aktuelles_sj = date(jahr, 8, 1)

# letztes Schuljahr
beginn_letztes_sj = date(beginn_aktuelles_sj.year - 1, 8, 1)

# vorletztes Schuljahr – ALLES davor ist „Karteileiche“
beginn_vorletztes_sj = date(beginn_aktuelles_sj.year - 2, 8, 1)

# JSON-Zähler für gelöschte Aufgaben
COUNTER_FILE = (
    Path(__file__)
    .resolve()
    .parents[3]
    / "core"
    / "zaehler_geloeschte_aufgaben.json"
)

if not COUNTER_FILE.exists():
    COUNTER_FILE.write_text(json.dumps({"anzahl": 0}))


def add_geloeschte_aufgaben(n):
    data = json.loads(COUNTER_FILE.read_text())
    data["anzahl"] += n
    COUNTER_FILE.write_text(json.dumps(data))


class Command(BaseCommand):
    help = "Löscht SCHÜLER (>1 Jahr inaktiv) — Lehrer und Admins bleiben!"

    def handle(self, *args, **options):

        # Grenze für Inaktivität: 1 Jahr
        grenze = timezone.now() - timedelta(days=365)

        # Lehrer-Gruppe holen
        try:
            gruppe_lehrer = Group.objects.get(name="Lehrer")
        except Group.DoesNotExist:
            self.stdout.write("WARNUNG: Gruppe 'Lehrer' existiert nicht.")
            return

        # Nur SCHÜLER auswählen
        schueler_profile = (
            Profil.objects
            .exclude(user__groups=gruppe_lehrer)     # Lehrer überspringen
            .exclude(user__is_staff=True)           # Staff-Accounts schützen
            .exclude(user__is_superuser=True)       # Admin schützen
            .select_related("user", "gruppe__lehrer")
        )

        geloeschte_profile = 0
        gesamt_geloeschte_aufgaben = 0

        # Alle Profile durchgehen
        for profil in schueler_profile:
            user = profil.user

            # Letzte Aufgabe des Schülers finden (Feld heißt "start")
            letzte = (
                Protokoll.objects
                .filter(profil=profil)
                .order_by("-start")
                .first()
            )

            # FALL A: Schüler hat NIE gerechnet → Löschprüfung über Anmeldedatum
            if letzte is None:
                if user.date_joined.date() >= beginn_vorletztes_sj:
                    continue
                letzte_datum = None

            # FALL B: Schüler hat gerechnet → Löschprüfung über letzte Aufgabe
            else:
                if letzte.start.date() >= beginn_vorletztes_sj:
                    continue
                letzte_datum = letzte.start.date()

            # AUFGABEN zählen und löschen
            protokolle = Protokoll.objects.filter(profil=profil)
            anzahl_aufgaben = protokolle.count()

            # Hochzählen in JSON-Datei
            gesamt_geloeschte_aufgaben += anzahl_aufgaben
            add_geloeschte_aufgaben(anzahl_aufgaben)

            protokolle.delete()

            # Infos für Geloescht-Eintrag
            gruppe = profil.gruppe.name if profil.gruppe else "–"
            lehrer = profil.gruppe.lehrer.username if profil.gruppe else "–"

            if letzte_datum:
                datum_text = f"Letzte Aufgabe: {letzte_datum}"
            else:
                datum_text = "Nie eine Aufgabe gerechnet"

            text = (
                f"Schüler {profil.vorname} {profil.nachname} "
                f"({user.username}, Klasse {profil.klasse}, Gruppe {gruppe}, Lehrer {lehrer}) "
                f"– {datum_text}. "
                f"{anzahl_aufgaben} Aufgaben gelöscht. "
                f"Account wegen Inaktivität (>1 Jahr) entfernt."
            )

            # In Geloescht speichern
            Geloescht.objects.create(
                benutzername=user.username,
                text=text,
            )

            # Profil + User löschen
            profil.delete()
            user.delete()

            geloeschte_profile += 1
            self.stdout.write(text)

        # FINALER Abschlussbericht
        self.stdout.write("")
        self.stdout.write("-----------------------------------------------------")
        self.stdout.write(f"   Insgesamt gelöschte Schüler:  {geloeschte_profile}")
        self.stdout.write(f"   Insgesamt gelöschte Aufgaben: {gesamt_geloeschte_aufgaben}")
        self.stdout.write("-----------------------------------------------------")
        self.stdout.write("")
