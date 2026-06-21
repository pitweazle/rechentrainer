from django.core.management.base import BaseCommand
from accounts.models import Profil
from accounts.models import Lerngruppe
class Command(BaseCommand):
    help = 'Trägt Schulen nach und analysiert Schüler ohne Gruppen sowie Lehrer.'

    def handle(self, *args, **options):
        # --- 1. STATISTIK & ANALYSE ---
        
        # Alle Lehrer-IDs ermitteln, die in den Lerngruppen eingetragen sind
        lehrer_ids = Lerngruppe.objects.values_list('lehrer_id', flat=True).distinct()
        anzahl_lehrer = len(lehrer_ids)
        
        # Schüler ohne Gruppe und ohne Schule ermitteln (die auch keine Lehrer sind)
        schueler_ohne_alles = Profil.objects.filter(
            gruppe__isnull=True, 
            schule__isnull=True
        ).exclude(user_id__in=lehrer_ids)
        
        anzahl_schueler_ohne_gruppe = schueler_ohne_alles.count()

        self.stdout.write(self.style.MIGRATE_HEADING("--- Datenbank-Analyse ---"))
        self.stdout.write(f"Aktive Lehrer im System: {anzahl_lehrer}")
        self.stdout.write(f"Schüler ohne Lerngruppe & ohne Schule: {anzahl_schueler_ohne_gruppe}")
        self.stdout.write("-------------------------\n")

        # --- 2. SCHULZUORDNUNG AUSFÜHREN ---
        self.stdout.write(self.style.MIGRATE_HEADING("--- Starte Schulzuordnung ---"))
        
        # Wir holen alle Profile, die keine Schule haben, aber einer Gruppe zugeordnet sind
        profil_liste = Profil.objects.filter(schule__isnull=True, gruppe__isnull=False)
        
        erfolgreich_aktualisiert = 0

        for profil in profil_liste:
            lerngruppe = profil.gruppe
            
            if lerngruppe.lehrer and hasattr(lerngruppe.lehrer, 'profil') and lerngruppe.lehrer.profil.schule:
                lehrer_schule = lerngruppe.lehrer.profil.schule
                
                profil.schule = lehrer_schule
                profil.save()
                erfolgreich_aktualisiert += 1
                
                self.stdout.write(
                    f"User '{profil.user.username}' -> Schule '{lehrer_schule.schulname}'"
                )

        self.stdout.write("\n-------------------------")
        self.stdout.write(
            self.style.SUCCESS(f'Fertig! {erfolgreich_aktualisiert} Profile erfolgreich aktualisiert.')
        )