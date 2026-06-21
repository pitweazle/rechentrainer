from django.core.management.base import BaseCommand
from accounts.models import Schule 

class Command(BaseCommand):
    help = 'Trägt die standardisierten SSO-Schulnummern für bestehende Schulen ein'

    def handle(self, *args, **options):
        # Wir holen alle Schulen, die noch keine Dienststellennummer haben
        schulen = Schule.objects.filter(dienststellen_nr__isnull=True)
        
        if not schulen.exists():
            self.stdout.write(self.style.SUCCESS("Alle Schulen haben bereits eine Nummer!"))
            return

        self.stdout.write(f"{schulen.count()} Schulen ohne Nummer gefunden.\n")
        self.stdout.write("Format-Tipp: DE-HE-4325 (Hessen), DE-NW-112450 (NRW), CH-1234 (Schweiz)\n")
        self.stdout.write("-" * 60)
        
        for schule in schulen:
            ort_name = schule.ort.name if schule.ort else "Unbekannt"
            self.stdout.write(f"\n-> Schule: {schule.schulname} ({ort_name})")
            
            # Eingabe im Terminal abfragen
            nr = input("Bitte SSO-ID eingeben (oder ENTER zum Überspringen): ").strip()
            
            if nr:
                # Wir speichern das eingegebene Format (z.B. DE-HE-4325)
                schule.dienststellen_nr = nr
                schule.save()
                self.stdout.write(self.style.SUCCESS(f"   Gespeichert: {nr}"))
            else:
                self.stdout.write("   Übersprungen.")
                
        self.stdout.write(f"\n" + "="*60 + "\nDurchlauf beendet!")