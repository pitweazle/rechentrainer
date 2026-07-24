from django.core.management.base import BaseCommand
import secrets
import string
from accounts.models import Schule

class Command(BaseCommand):
    help = "Generiert Shared Secrets für Schulen."

    def handle(self, *args, **options):
        count = 0
        for schule in Schule.objects.all():
            # Shared Secret für alle setzen (überschreibt auch bestehende, 
            # falls du sie gezielt ersetzen willst)
            schule.shared_secret = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(24))
            schule.save()
            count += 1

        self.stdout.write(self.style.SUCCESS(f"Erfolgreich für {count} Schulen ein neues Shared Secret generiert!"))