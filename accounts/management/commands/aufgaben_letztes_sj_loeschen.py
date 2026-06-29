from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime
from django.db import transaction
from django.db.models import Count
from django.conf import settings

import json
from pathlib import Path

# Imports passend zu deiner Struktur
from core.models import Protokoll
from accounts.models import Geloescht
from accounts.services import get_today 

class Command(BaseCommand):
    help = 'Archiviert alte Protokolle vor dem 1. Juni des letzten Schuljahres (wird am 1.8. ausgeführt)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--commit',
            action='store_true',
            help='Schreibt die Änderungen tatsächlich in die Datenbank und löscht die alten Protokolle',
        )

    def handle(self, *args, **options):
        commit = options['commit']
        heute = get_today()

        # 1. JSON-Zähler-Pfad auslesen
        json_pfad = Path(settings.BASE_DIR) / "core" / "zaehler_geloeschte_aufgaben.json"
        
        if not json_pfad.exists():
            self.stdout.write(self.style.ERROR(f"FEHLER: Basis-JSON nicht gefunden unter {json_pfad}"))
            return

        try:
            json_daten = json.loads(json_pfad.read_text(encoding='utf-8'))
            zaehler_vorher = json_daten.get('anzahl', 0)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Fehler beim Lesen der JSON: {e}"))
            return

        # 2. Stichtag berechnen (1. Juni des Vorjahres)
        stichtag_jahr = heute.year - 1
        stichtag = datetime(stichtag_jahr, 6, 1, 0, 0, tzinfo=timezone.get_current_timezone())

        self.stdout.write(f"Starte Archivierung am: {heute.strftime('%d.%m.%Y')}")
        self.stdout.write(f"Stichtag (alles davor wird gelöscht): {stichtag.strftime('%d.%m.%Y')}")
        self.stdout.write("-" * 85)

        # 3. Relevante, alte Protokolle ermitteln
        alte_protokolle = Protokoll.objects.filter(start__lt=stichtag)
        gesamt_anzahl = alte_protokolle.count()

        if gesamt_anzahl == 0:
            self.stdout.write(self.style.SUCCESS("Keine alten Protokolle zum Archivieren gefunden."))
            return

        # 4. Aggregieren nach Schüler (Profil) und Kategorie
        daten_schleife = (
            alte_protokolle
            .values('profil_id', 'kategorie_id')
            .annotate(anzahl=Count('id'))
            .order_by('profil_id', 'kategorie_id')
        )

        zaehler_nachher = zaehler_vorher + gesamt_anzahl

        # 5. Daten im Speicher nach Schüler gruppieren
        schueler_logs = {}
        from accounts.models import Profil

        for eintrag in daten_schleife:
            pid = eintrag['profil_id']
            kid = eintrag['kategorie_id']
            anzahl_geloescht = eintrag['anzahl']

            if not pid:
                continue

            if pid not in schueler_logs:
                try:
                    schueler = Profil.objects.get(id=pid)
                    vname = schueler.vorname or ""
                    nname = schueler.nachname or ""
                    schueler_name = f"{vname} {nname}".strip() or f"User-ID {pid}"
                    
                    if schueler.gruppe:
                        gruppe_name = schueler.gruppe.name
                        lehrer_nachname = schueler.gruppe.lehrer.profil.nachname if schueler.gruppe.lehrer.profil else schueler.gruppe.lehrer.username
                    else:
                        gruppe_name = "Keine Gruppe"
                        lehrer_nachname = "Ohne Lehrer"
                except Exception:
                    schueler_name = f"User-ID {pid}"
                    gruppe_name = "Unbekannt"
                    lehrer_nachname = "Unbekannt"

                schueler_logs[pid] = {
                    'name_display': schueler_name,
                    'gruppe': gruppe_name,
                    'lehrer': lehrer_nachname,
                    'kategorien': [],
                    'schueler_gesamt': 0
                }
            
            schueler_logs[pid]['kategorien'].append(f"({kid}/{anzahl_geloescht})")
            schueler_logs[pid]['schueler_gesamt'] += anzahl_geloescht

        # Globaler Log-Text Vorher/Nachher
        globaler_log_text = (
            f"Archivierung Schuljahr am {heute.strftime('%d.%m.%Y')}: "
            f"Zähler VORHER: {zaehler_vorher} | "
            f"JETZT gelöscht: {gesamt_anzahl} | "
            f"Zähler NACHHER: {zaehler_nachher}."
        )

        # 6. Ausgeben und Schreiben (Transaktion)
        try:
            with transaction.atomic():
                self.stdout.write("\nEINZELAUFLISTUNG DER BETROFFENEN SCHÜLER:")
                self.stdout.write("-" * 85)
                
                counter_logs = 0
                for pid, info in schueler_logs.items():
                    kat_text = ", ".join(info['kategorien'])
                    gruppe_lehrer_display = f"{info['gruppe']}/{info['lehrer']}"
                    
                    # Log-Text für das Feld 'text' ohne Namens-Redundanz
                    log_text_schueler = (
                        f"Gesamt gelöscht: {info['schueler_gesamt']} | "
                        f"Details (Kategorie/Anzahl): {kat_text}"
                    )

                    # Kombination für das Feld 'benutzername' in der DB
                    db_benutzername = f"{info['name_display']} ({gruppe_lehrer_display})"[:50]

                    # Ausgabe auf dem Bildschirm zur Kontrolle
                    self.stdout.write(
                        f"Schüler: {info['name_display']:<25} | "
                        f"Gruppe/Lehrer: {gruppe_lehrer_display:<20} | "
                        f"Gesamt: {info['schueler_gesamt']:<4} | "
                        f"Kategorien: {kat_text}"
                    )

                    if commit:
                        # Schüler-Eintrag speichern
                        Geloescht.objects.create(
                            benutzername=db_benutzername,
                            grund="Aufgaben aus dem letzten Schuljahr gelöscht",
                            text=log_text_schueler
                        )
                    counter_logs += 1

                # Globale Zusammenfassung ganz unten im Terminal
                self.stdout.write("\n" + "="*85)
                self.stdout.write(f"ZUSAMMENFASSUNG DER SCHULJAHR-BEREINIGUNG:")
                self.stdout.write(globaler_log_text)
                self.stdout.write(f"Anzahl erstellter Schüler-Logs: {counter_logs}")
                self.stdout.write("="*85 + "\n")

                if commit:
                    # Der globale Eintrag für die Gesamtsumme
                    Geloescht.objects.create(
                        benutzername="cronjob",
                        grund="Aufgaben aus dem letzten Schuljahr gelöscht",
                        text=globaler_log_text
                    )

                    # Den neuen Wert zurück in die JSON-Datei schreiben
                    neue_json_daten = {'anzahl': zaehler_nachher}
                    with open(json_pfad, 'w', encoding='utf-8') as f:
                        json.dump(neue_json_daten, f, indent=4)
                        
                    # Jetzt werden die alten Protokolle physisch gelöscht
                    alte_protokolle.delete()
                    self.stdout.write(self.style.SUCCESS(f"[LIVE] Archivierung erfolgreich durchgeführt. {gesamt_anzahl} Zeilen gelöscht."))
                else:
                    raise RuntimeError("Sicherheits-Rollback")

        except RuntimeError as e:
            if str(e) == "Sicherheits-Rollback":
                self.stdout.write("\n" + "#" * 60)
                self.stdout.write(self.style.WARNING("!!! NUR SIMULATION (TROCKENLAUF) - ES WURDE NICHTS IN DIE DB ODER JSON GESCHRIEBEN !!!"))
                self.stdout.write("#" * 60)
            else:
                raise e