from datetime import timedelta
from django.utils import timezone
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.conf import settings
from django.db.models import Sum

from accounts.models import Profil, Geloescht
from core.models import Protokoll, Kategorie

import json
from pathlib import Path

heute = timezone.now().date()
COUNTER_FILE = Path(settings.BASE_DIR) / "core" / "zaehler_geloeschte_aufgaben.json"

if not COUNTER_FILE.exists():
    COUNTER_FILE.write_text(json.dumps({"anzahl": 0}))


def add_geloeschte_aufgaben(n):
    data = json.loads(COUNTER_FILE.read_text())
    data["anzahl"] += n
    COUNTER_FILE.write_text(json.dumps(data))


class Command(BaseCommand):
    help = "Löscht SCHÜLER mit >366 Tagen Inaktivität (Lehrer/Admins bleiben) und aktualisiert Kategorie-Zähler"

    def handle(self, *args, **options):
        grenze = timezone.now().date() - timedelta(days=366)  
        try:
            gruppe_lehrer = Group.objects.get(name="Lehrer")
        except Group.DoesNotExist:
            self.stdout.write("WARNUNG: Gruppe 'Lehrer' existiert nicht.")
            return

        schueler_profile = (
            Profil.objects
            .exclude(user__groups=gruppe_lehrer)
            .exclude(user__is_staff=True)
            .exclude(user__is_superuser=True)
            .select_related("user", "gruppe__lehrer")
        )

        geloeschte_profile = 0
        gesamt_geloeschte_aufgaben = 0

        for profil in schueler_profile:
            user = profil.user

            letzte = (
                Protokoll.objects
                .filter(profil=profil)
                .order_by("-start")
                .first()
            )

            if letzte is None:
                if user.date_joined.date() >= grenze:
                    continue
                letzte_datum = None
            else:
                if letzte.start.date() >= grenze:
                    continue
                letzte_datum = letzte.start.date()

            protokolle = Protokoll.objects.filter(profil=profil)
            anzahl_aufgaben = protokolle.count()

            # --- NEU: ZUERST die Kategorien-Zähler aktualisieren, solange die Protokolle da sind ---
            kategorien_verteilung = (
                protokolle
                .values('kategorie_id')
                .annotate(anzahl=Sum(1))
            )

            for eintrag in kategorien_verteilung:
                kid = eintrag['kategorie_id']
                count = eintrag['anzahl']
                
                if not kid:
                    continue

                try:
                    kat = Kategorie.objects.get(id=kid)
                    kat.geloeschte_aufgaben += count
                    kat.save()
                except Kategorie.DoesNotExist:
                    pass
            # --------------------------------------------------------------------------------------

            gesamt_geloeschte_aufgaben += anzahl_aufgaben
            add_geloeschte_aufgaben(anzahl_aufgaben)
            protokolle.delete()

            gruppe = profil.gruppe.name if profil.gruppe else "–"
            lehrer = profil.gruppe.lehrer.username if profil.gruppe else "–"

            if letzte_datum:
                datum_text = f"Letzte Aufgabe: {letzte_datum}"
            else:
                datum_text = "Nie eine Aufgabe gerechnet"

            text = (
                f"Schüler {profil.vorname} {profil.nachname} "
                f"({user.username}, Klasse {profil.klasse}, Gruppe {gruppe}, Lehrer {lehrer}) – "
                f"{datum_text}. {anzahl_aufgaben} Aufgaben gelöscht. "
                f"Account wegen Inaktivität (>366 Tage) entfernt."
            )

            Geloescht.objects.create(
                benutzername="cronjob",
                grund="schueler_inaktiv",
                text=text,
            )

            profil.delete()
            user.delete()
            geloeschte_profile += 1

        self.stdout.write("")
        self.stdout.write("-----------------------------------------------------")
        self.stdout.write(f"Insgesamt gelöschte Schüler:  {geloeschte_profile}")
        self.stdout.write(f"Insgesamt gelöschte Aufgaben: {gesamt_geloeschte_aufgaben}")
        self.stdout.write("-----------------------------------------------------")
        self.stdout.write("")
        
        Geloescht.objects.create(
            benutzername="cronjob",
            grund="inaktive Schüler",
            text=(f"{heute} insgesamt gelöscht: {geloeschte_profile} Schüler, {gesamt_geloeschte_aufgaben} Aufgaben"),
        )