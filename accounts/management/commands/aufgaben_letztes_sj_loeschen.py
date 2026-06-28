from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime
from django.db import transaction
from django.db.models import Count, F

# Passe die Imports an deine App-Struktur an!
from core.models import Protokoll, Zaehler 
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

        # 1. Stichtag berechnen (1. Juni des Vorjahres)
        heute = get_today()
        stichtag_jahr = heute.year - 1
        stichtag = datetime(stichtag_jahr, 6, 1, 0, 0, tzinfo=timezone.get_current_timezone())

        self.stdout.write(f"Starte Archivierung am: {heute.strftime('%d.%m.%Y')}")
        self.stdout.write(f"Stichtag (alles davor wird gelöscht): {stichtag.strftime('%d.%m.%Y')}")
        self.stdout.write("-" * 85)

        # 2. Relevante, alte Protokolle ermitteln
        alte_protokolle = Protokoll.objects.filter(start__lt=stichtag)
        gesamt_anzahl = alte_protokolle.count()

        if gesamt_anzahl == 0:
            self.stdout.write(self.style.SUCCESS("Keine alten Protokolle zum Archivieren gefunden."))
            return

        # 3. Aggregieren nach Schüler (Profil) und Kategorie
        daten_schleife = (
            alte_protokolle
            .filter(richtig=True) 
            .values('profil_id', 'kategorie_id')
            .annotate(anzahl=Count('id'))
            .order_by('profil_id', 'kategorie_id')
        )

        # 4. Daten im Speicher nach Schüler gruppieren
        schueler_logs = {}
        from accounts.models import Profil

        for eintrag in daten_schleife:
            pid = eintrag['profil_id']
            kid = eintrag['kategorie_id']
            anzahl_geloescht = eintrag['anzahl']

            if not pid:
                continue

            if pid not in schueler_logs:
                # Schüler-Details einmalig beim ersten Treffen herbeiholen
                try:
                    schueler = Profil.objects.get(id=pid)
                    vname = schueler.vorname or ""
                    nname = schueler.nachname or ""
                    schueler_name = f"{vname} {nname}".strip() or f"User-ID {pid}"
                    bname = getattr(schueler.user, 'username', f"user_id_{pid}")
                    
                    if schueler.gruppe:
                        gruppe_name = schueler.gruppe.name
                        lehrer_nachname = schueler.gruppe.lehrer.profil.nachname if schueler.gruppe.lehrer.profil else schueler.gruppe.lehrer.username
                    else:
                        gruppe_name = "Keine Gruppe"
                        lehrer_nachname = "Ohne Lehrer"
                    
                    schule_name = getattr(schueler, 'schule', "Deine Schule")
                except Exception:
                    schueler_name = f"User-ID {pid}"
                    bname = f"user_id_{pid}"
                    gruppe_name = "Unbekannt"
                    lehrer_nachname = "Unbekannt"
                    schule_name = "Unbekannt"

                schueler_logs[pid] = {
                    'username': bname,
                    'name_display': schueler_name,
                    'gruppe': gruppe_name,
                    'lehrer': lehrer_nachname,
                    'schule': schule_name,
                    'kategorien': [],
                    'updates': [] # Für den Zähler-Commit im nächsten Schritt
                }
            
            # Kategorien und Zähler-Updates sammeln
            schueler_logs[pid]['kategorien'].append(f"({kid}/{anzahl_geloescht})")
            schueler_logs[pid]['updates'].append({'kid': kid, 'anzahl': anzahl_geloescht})

        # 5. Datenbank-Transaktion starten & gebündelt schreiben
        try:
            with transaction.atomic():
                counter_logs = 0
                
                for pid, info in schueler_logs.items():
                    # 1. Alle Klammer-Paare mit Komma trennen
                    kat_text = ", ".join(info['kategorien'])
                    
                    # 2. Die Gesamtzahl aller Aufgaben berechnen
                    schueler_gesamtzahl = sum(up['anzahl'] for up in info['updates'])
                    
                    # Log-Text für das Modell "Geloescht"
                    log_text = (
                        f"Archiviert (kat-nr/Anzahl der Aufgaben): {kat_text}. "
                        f"Gesamtzahl richtiger Aufgaben: {schueler_gesamtzahl}. "
                        f"Kontext: Lerngruppe {info['gruppe']}, Lehrer: {info['lehrer']}, Schule: {info['schule']}."
                    )

                    # Kombination aus Gruppe und Lehrer-Nachname für das Terminal bauen
                    gruppe_lehrer_display = f"{info['gruppe']}/{info['lehrer']}"

                    # JETZT FEHLERFREI: Nur ein 'f' ganz am Anfang der Zeile
                    self.stdout.write(
                        f"Schüler: {info['name_display']:<25} | "
                        f"Gruppe/Lehrer: {gruppe_lehrer_display:<20} | "
                        f"Gesamt: {schueler_gesamtzahl:<4} | "
                        f"Archiviert (kat-nr/Anzahl der Aufgaben): {kat_text}"
                    )

                    if commit:
                        # 1. Einzelne mathematische Zähler in der DB aktualisieren
                        for up in info['updates']:
                            zaehler, created = Zaehler.objects.get_or_create(
                                profil_id=pid,
                                kategorie_id=up['kid'],
                                defaults={'geloeschte_aufgaben': up['anzahl']}
                            )
                            if not created:
                                Zaehler.objects.filter(id=zaehler.id).update(
                                    geloeschte_aufgaben=F('geloeschte_aufgaben') + up['anzahl']
                                )
                        
                        # 2. EINZIGER kompakter Log-Eintrag für diesen Schüler
                        Geloescht.objects.create(
                            benutzername=info['username'],
                            grund="Aufgaben aus dem letzten Schuljahr gelöscht",
                            text=log_text
                        )
                    
                    counter_logs += 1

                # Zusammenfassung ganz unten
                self.stdout.write("=" * 85)
                self.stdout.write(self.style.SUCCESS(f"GESAMTZAHL DER ZU LÖSCHENDEN PROTOKOLLZEILEN: {gesamt_anzahl}"))
                self.stdout.write(f"Anzahl erstellter Log-Einträge in 'Geloescht': {counter_logs}")
                self.stdout.write("=" * 85)

                if commit:
                    alte_protokolle.delete()
                    self.stdout.write(self.style.SUCCESS(f"\n[LIVE] Archivierung erfolgreich durchgeführt. {gesamt_anzahl} Zeilen gelöscht."))
                else:
                    raise RuntimeError("Sicherheits-Rollback")

        except RuntimeError as e:
            if str(e) == "Sicherheits-Rollback":
                self.stdout.write("\n" + "#" * 60)
                self.stdout.write(self.style.WARNING("!!! NUR SIMULATION - ES WURDE NICHTS IN DIE DATENBANK GESCHRIEBEN !!!"))
                self.stdout.write(self.style.WARNING("Um diese Änderungen live anzuwenden, füge '--commit' hinzu."))
                self.stdout.write("#" * 60)
            else:
                raise e