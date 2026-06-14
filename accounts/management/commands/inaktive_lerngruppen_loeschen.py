from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import Profil
from core.models import Lerngruppe
from accounts.models import Geloescht


class Command(BaseCommand):
    help = "Löscht verwaiste Lerngruppen, protokolliert sie in der Geloescht-Datenbank und gibt eine Übersicht aus."

    def add_arguments(self, parser):
        # Ein Sicherheits-Flag, damit man nicht aus Versehen löscht
        parser.add_argument(
            '--commit',
            action='store_true',
            help='Führt das Löschen und Protokollieren tatsächlich aus. Ohne dieses Flag läuft nur ein Test.',
        )

    def handle(self, *args, **options):
        # Sicherheits-Zeitraum
        TAGE_GRENZE = 90  
        commit = options['commit']
        
        gesamtzahl_gruppen = Lerngruppe.objects.count()
        grenze = timezone.now().date() - timedelta(days=TAGE_GRENZE)
        
        # Alle Lerngruppen, die älter als X Tage sind
        alte_lerngruppen = Lerngruppe.objects.filter(erstellt_am__lt=grenze)
        
        kandidaten_anzahl = 0
        gruppen_ohne_schüler = []
        
        for gruppe in alte_lerngruppen:
            # Prüfen, ob die Lerngruppe Schüler hat
            hat_schüler = Profil.objects.filter(gruppe=gruppe).exists()
            
            if not hat_schüler:
                gruppen_ohne_schüler.append(gruppe)
                kandidaten_anzahl += 1
        
        # Ausgabe der Übersicht
        self.stdout.write("\n---------------------------------------------------")
        self.stdout.write(f"Gesamtzahl aller Lerngruppen im System:      {gesamtzahl_gruppen}")
        self.stdout.write(f"Davon älter als {TAGE_GRENZE} Tage:                    {alte_lerngruppen.count()}")
        self.stdout.write(f"Davon ohne Schüler (Kandidaten):              {kandidaten_anzahl}")
        self.stdout.write("---------------------------------------------------")
        
        if not commit:
            self.stdout.write("\n*** TOCKENÜBUNG: Es wurde nichts gelöscht. Nutze --commit zum Löschen. ***")
        
        if gruppen_ohne_schüler:
            action_word = "Gelöscht" if commit else "Kandidat"
            self.stdout.write(f"\nFolgende Lerngruppen ({action_word}):")
            
            for gruppe in gruppen_ohne_schüler:
                lehrer = gruppe.lehrer
                
                # Klarnamen für das Terminal holen
                try:
                    lehrer_klarname = f"{lehrer.profil.vorname} {lehrer.profil.nachname}".strip()
                except Profil.DoesNotExist:
                    lehrer_klarname = lehrer.username
                
                if not lehrer_klarname or lehrer_klarname == " ":
                    lehrer_klarname = lehrer.username

                # Text für deine Geloescht-Datenbank vorbereiten
                log_text = (
                    f"Lerngruppe gelöscht: '{gruppe.name}' (ID: {gruppe.id}). "
                    f"Erstellt am: {gruppe.erstellt_am}. "
                    f"Lehrer: {lehrer_klarname} (Username: {lehrer.username})."
                )
                
                if commit:
                    # 1. Eintrag in die 'Geloescht' DB schreiben
                    Geloescht.objects.create(
                        benutzername=lehrer.username,
                        grund="Inaktivität Lerngruppe",
                        text=log_text,
                        erstellt_am=timezone.now()
                    )
                    # 2. Lerngruppe endgültig löschen
                    gruppe.delete()
                
                # Ausgabe im Terminal
                self.stdout.write(f"- \"{gruppe.name}\" (Lehrer: {lehrer_klarname}) -> In DB 'Geloescht' aufgenommen.")
                
            if commit:
                self.stdout.write(f"\nErfolgreich {kandidaten_anzahl} Lerngruppen gelöscht und protokolliert.")
        else:
            self.stdout.write(f"\nKeine Lerngruppen gefunden, die älter als {TAGE_GRENZE} Tage sind und keine Schüler haben.")
        
        self.stdout.write("\n---------------------------------------------------")