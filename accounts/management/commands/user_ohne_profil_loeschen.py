from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone

from accounts.models import Geloescht  # Profil brauchst du hier eigentlich nicht

class Command(BaseCommand):
    help = "Löscht User ohne Profil (unvollständige Anmeldungen) und protokolliert das"
    def handle(self, *args, **options):
        users_ohne_profil = User.objects.filter(
            profil__isnull=True,
            is_superuser=False,
            #is_staff=False,  # falls du is_staff nicht nutzt, kannst du diese Zeile zur Not auch weglassen
        )
        anzahl = 0
        for user in users_ohne_profil:
            text = (
                f"User '{user.username}' hat kein Profil "
                f"und wurde am {timezone.now().date()} als unvollständige Anmeldung gelöscht."
            )
            Geloescht.objects.create(
                benutzername=user.username,
                grund="unvollstaendig - kein Profil"
                text=text,
            )
            user.delete()
            anzahl += 1
            self.stdout.write(text)
        self.stdout.write(f"{anzahl} User ohne Profil gelöscht.")
