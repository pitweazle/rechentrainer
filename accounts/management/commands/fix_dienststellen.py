from django.core.management.base import BaseCommand
import secrets
import string
from accounts.models import Schule

class Command(BaseCommand):
    help = "Setzt temporäre Dienststellennummern und Secrets für Schulen ohne Nummer."

    def handle(self, *args, **options):
        count = 0
        for schule in Schule.objects.all():
            if not schule.dienststellen_nr:
                # Erst speichern, damit die Schule einen PK bekommt, falls sie neu ist
                if not schule.pk:
                    schule.save()
                schule.dienststellen_nr = f"Fake-{schule.pk}"

            if not schule.shared_secret:
                schule.shared_secret = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32))

            schule.save()
            count += 1

        self.stdout.write(self.style.SUCCESS(f"Erfolgreich {count} Schulen verarbeitet!"))