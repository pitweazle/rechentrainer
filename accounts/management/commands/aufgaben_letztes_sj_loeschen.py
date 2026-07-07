from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime
from django.db import transaction
from django.db.models import Sum  # NEU: Zum Aufsummieren der richtigen/falschen Aufgaben
from django.conf import settings

import json
from pathlib import Path

# Imports passend zu deiner Struktur
from core.models import Protokoll, Zaehler
from accounts.models import Geloescht
from accounts.services import get_today 
from core.models import Profil 

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

        # 1. JSON-Zähler-Pfad sauber definieren & auslesen
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

        # 2. Stichtag berechnen: 1. Juni des VORJAHRES
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
        # ANPASSUNG: Wir zählen nicht nur die Zeilen, sondern addieren die Werte aus 'richtig' und 'falsch' auf!
        daten_schleife = (
            alte_protokolle
            .values('profil_id', 'kategorie_id')
            .annotate(
                anzahl_zeilen=Sum(1),  # Wie viele Zeilen werden gelöscht
                summe_richtig=Sum('richtig'),
                summe_falsch=Sum('falsch')
            )
            .order_by('profil_id', 'kategorie_id')
        )

        zaehler_nachher = zaehler_vorher + gesamt_anzahl

        # 5. Daten im Speicher nach Schüler gruppieren
        schueler_logs = {}

        for eintrag in daten_schleife:
            pid = eintrag['profil_id']
            kid = eintrag['kategorie_id']
            anzahl_geloescht = eintrag['anzahl_zeilen']
            r_sum = int(eintrag['summe_richtig'] or 0)
            f_sum = int(eintrag['summe_falsch'] or 0)

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
                    'profil_objekt': schueler if 'schueler' in locals() else None,
                    'name_display': schueler_name,
                    'gruppe': gruppe_name,
                    'lehrer': lehrer_nachname,
                    'kategorien': [],
                    'kategorien_rohdaten': [],
                    'schueler_gesamt': 0,
                    'total_richtig': 0,  # Summenspeicher für das Profil
                    'total_falsch': 0    # Summenspeicher für das Profil
                }
            
            schueler_logs[pid]['kategorien'].append(f"({kid}/{anzahl_geloescht})")
            schueler_logs[pid]['kategorien_rohdaten'].append((kid, anzahl_geloescht))
            schueler_logs[pid]['schueler_gesamt'] += anzahl_geloescht
            schueler_logs[pid]['total_richtig'] += r_sum
            schueler_logs[pid]['total_falsch'] += f_sum

        # Jeder Schüler wird sauber im Terminal aufgelistet
        self.stdout.write("\nEINZELAUFLISTUNG DER BETROFFENEN SCHÜLER:")
        self.stdout.write("-" * 85)
        
        missing_counters_found = False

        for pid, info in schueler_logs.items():
            kat_text = ", ".join(info['kategorien'])
            gruppe_lehrer_display = f"{info['gruppe']}/{info['lehrer']}"
            self.stdout.write(
                f"Schüler: {info['name_display']:<25} | "
                f"Gruppe/Lehrer: {gruppe_lehrer_display:<20} | "
                f"Zeilen: {info['schueler_gesamt']:<4} (r: {info['total_richtig']}/f: {info['total_falsch']}) | "
                f"Kategorien: {kat_text}"
            )
            
            # ÜBERPRÜFUNG IM TROCKENLAUF: Existieren alle Zähler?
            for kid, _ in info['kategorien_rohdaten']:
                if not Zaehler.objects.filter(profil_id=pid, kategorie_id=kid).exists():
                    self.stdout.write(self.style.ERROR(
                        f"   [WARNUNG] Fehlender Zähler für Schüler '{info['name_display']}' (ID: {pid}) bei Kategorie {kid}!"
                    ))
                    missing_counters_found = True

        # Der exakte Text für deinen EINEN globalen Sicherheits-Eintrag
        globaler_log_text = (
            f"Archivierung Schuljahr am {heute.strftime('%d.%m.%Y')}: "
            f"Zähler VORHER: {zaehler_vorher} | "
            f"JETZT gelöscht: {gesamt_anzahl} | "
            f"Zähler NACHHER: {zaehler_nachher}."
        )

        # Globale Zusammenfassung ganz unten im Terminal
        self.stdout.write("\n" + "="*85)
        self.stdout.write(f"ZUSAMMENFASSUNG DER SCHULJAHR-BEREINIGUNG:")
        self.stdout.write(globaler_log_text)
        self.stdout.write("="*85 + "\n")

        if missing_counters_found and not commit:
            self.stdout.write(self.style.ERROR("!!! ACHTUNG: Es wurden fehlende Zähler-Objekte im Trockenlauf entdeckt (siehe rote Warnungen oben) !!!\n"))

        # 6. Datenbank-Transaktion starten & gebündelt schreiben
        if commit:
            try:
                with transaction.atomic():
                    # Einzelergebnisse in Zaehler verbuchen & Log pro Schüler schreiben
                    for pid, info in schueler_logs.items():
                        
                        # ANPASSUNG: Historische Werte direkt im Profil aufaddieren
                        if info['profil_objekt']:
                            schueler = info['profil_objekt']
                            schueler.historische_aufgaben_richtig += info['total_richtig']
                            schueler.historische_aufgaben_falsch += info['total_falsch']
                            schueler.save()

                        # A) Zähler pro Kategorie erhöhen
                        for kid, anzahl_geloescht in info['kategorien_rohdaten']:
                            try:
                                zaehler_objekt = Zaehler.objects.get(profil_id=pid, kategorie_id=kid)
                                zaehler_objekt.geloeschte_aufgaben += anzahl_geloescht
                                zaehler_objekt.save()
                            except Zaehler.DoesNotExist:
                                from core.models import Kategorie
                                try:
                                    kategorie = Kategorie.objects.get(id=kid)
                                except Kategorie.DoesNotExist:
                                    continue # Falls die Kategorie selbst nicht mehr existiert

                                # Zähler reparieren
                                Zaehler.objects.create(
                                    profil_id=pid,
                                    kategorie_id=kid,
                                    geloeschte_aufgaben=anzahl_geloescht,
                                    aufgnr=1,
                                )
                                
                                if info['profil_objekt'] and schueler.katmax <= kategorie.zeile:
                                    schueler.katmax = kategorie.zeile
                                    schueler.save()
                                    
                                self.stdout.write(self.style.WARNING(
                                    f"   [REPARIERT] Fehlender Zähler für Schüler '{info['name_display']}' (Kategorie {kid}) wurde automatisch erzeugt."
                                ))

                        # B) Schüler-Log in Geloescht schreiben
                        kat_text = ", ".join(info['kategorien'])
                        gruppe_lehrer_display = f"{info['gruppe']}/{info['lehrer']}"
                        db_benutzername = f"{info['name_display']} ({gruppe_lehrer_display})"[:50]
                        
                        Geloescht.objects.create(
                            benutzername=db_benutzername,
                            grund="Aufgaben aus dem letzten Schuljahr gelöscht",
                            text=f"Zeilen gelöscht: {info['schueler_gesamt']} (richtig: {info['total_richtig']}, falsch: {info['total_falsch']}) | Details: {kat_text}"
                        )

                    # DER EINE GLOBALE EINTRAG IN DIE DATENBANK
                    Geloescht.objects.create(
                        benutzername="cronjob",
                        grund="Aufgaben aus dem letzten Schuljahr gelöscht",
                        text=globaler_log_text
                    )

                    # Den neuen Wert zurück in die JSON-Datei schreiben
                    neue_json_daten = {
                        'anzahl': zaehler_nachher
                    }
                    with open(json_pfad, 'w', encoding='utf-8') as f:
                        json.dump(neue_json_daten, f, indent=4)
                        
                    # Jetzt werden die alten Protokolle physisch gelöscht
                    alte_protokolle.delete()
                    
                self.stdout.write(self.style.SUCCESS(f"[LIVE] Archivierung erfolgreich durchgeführt. {gesamt_anzahl} Zeilen gelöscht."))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Kritischer Fehler beim Speichern (Transaktion abgebrochen): {e}"))
        else:
            self.stdout.write(self.style.WARNING("!!! NUR SIMULATION (TROCKENLAUF) - ES WURDE NICHTS GESPEICHERT ODER GEÄNDERT !!!"))