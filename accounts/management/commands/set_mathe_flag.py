from django.core.management.base import BaseCommand
from accounts.models import Profil  # Passe den Import an, falls dein Profil in einer anderen App liegt

class Command(BaseCommand):
    help = 'Setzt das Mathe-Flag für alle bestehenden Benutzerprofile auf True.'

    def handle(self, *args, **kwargs):
        # Alle Profile holen, bei denen mathe noch False ist
        profile = Profil.objects.filter(mathe=False)
        anzahl = profile.count()
        
        if anzahl == 0:
            self.stdout.write(self.style.SUCCESS("Keine Profile zum Aktualisieren gefunden."))
            return

        self.stdout.write(f"Aktualisiere {anzahl} Profile...")
        
        # Effizientes Datenbank-Update für alle Bestandsuser
        updated_count = profile.update(mathe=True)
        
        self.stdout.write(self.style.SUCCESS(f"Erfolgreich! {updated_count} Profile wurden als Mathe-Nutzer markiert."))