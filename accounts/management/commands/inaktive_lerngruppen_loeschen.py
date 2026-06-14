from datetime import timedelta
from django.core.management.base import BaseCommand
from django.utils import timezone
from accounts.models import Profil
from core.models import Lerngruppe
from accounts.models import Geloescht


class Command(BaseCommand):
    help = "Löscht verwaiste Lerngruppen (älter als 30 Tage) und protokolliert sie in der Geloescht-Datenbank."

    def add_arguments(self, parser):
        # Nur noch das Testrun-Argument bleibt
        parser.add_argument(
            '--testrun',
            action='store_true',
            help='Führt nur eine Trockenübung aus, ohne wirklich zu löschen.',
        )

    def handle(self, *args, **options):
        TAGE_GRENZE = 30  
        # Logik für den Testlauf: Standardmäßig wird gelöscht
        commit = not options['testrun']
        
        gesamtzahl_gruppen = Lerngruppe.objects.count()
        grenze = timezone.now().date() - timedelta(days=TAGE_GRENZE)
        
        # Alle Lerngruppen, die älter als 30 Tage sind
        alte_lerngruppen = Lerngruppe.objects.filter(erstellt_am__lt=grenze)
        
        kandidaten_anzahl = 0
        gruppen_ohne_schüler = []
        
        for gruppe in alte_lerngruppen:
            # Prüfen, ob die Lerngruppe Schüler hat
            hat_schüler = Profil.objects.filter(gruppe=gruppe).exists()
            
            if not hat_schüler:
                gruppen_ohne_schüler.append(gruppe)
                kandidaten_anzahl += 1
        
        # Ausgabe der Ergebnisse
        self.stdout.write("\n---------------------------------------------------")
        self.stdout.write(f"Gesamtzahl aller Lerngruppen im System:      {gesamtzahl_gruppen}")
        self.stdout.write(f"Davon älter als {TAGE_GRENZE} Tage:                    {alte_lerngruppen.count()}")
        self.stdout.write(f"Davon ohne Schüler (Kandidaten):              {kandidaten_anzahl}")
        self.stdout.write("---------------------------------------------------")
        
        if not commit:
            self.stdout.write("\n*** TROCKENÜBUNG: Es wird nichts gelöscht! ***")
        
        if gruppen_ohne_schüler:
            action_word = "Gelöscht" if commit else "Kandidat"
            self.stdout.write(f"\nFolgende Lerngruppen ({action_word}):")
            
            for gruppe in gruppen_ohne_schüler:
                lehrer = gruppe.lehrer
                
                try:
                    lehrer_klarname = f"{lehrer.profil.vorname} {lehrer.profil.nachname}".strip()
                except Profil.DoesNotExist:
                    lehrer_klarname = lehrer.username
                
                if not lehrer_klarname or lehrer_klarname == " ":
                    lehrer_klarname = lehrer.username

                log_text = (
                    f"Lerngruppe automatisch gelöscht: '{gruppe.name}' (ID: {gruppe.id}). "
                    f"Erstellt am: {gruppe.erstellt_am}. "
                    f"Lehrer: {lehrer_klarname} (Username: {lehrer.username})."
                )
                
                if commit:
                    Geloescht.objects.create(
                        benutzername=lehrer.username,
                        grund="Inaktivität Lerngruppe",
                        text=log_text,
                        erstellt_am=timezone.now()
                    )
                    gruppe.delete()
                
                self.stdout.write(f"- \"{gruppe.name}\" (Lehrer: {lehrer_klarname})")
                
            if commit:
                self.stdout.write(f"\nErfolgreich {kandidaten_anzahl} Lerngruppen gelöscht und protokolliert.")
        else:
            self.stdout.write(f"\nKeine Lerngruppen gefunden, die älter als {TAGE_GRENZE} Tage sind und keine Schüler haben.")
        
        self.stdout.write("\n---------------------------------------------------")