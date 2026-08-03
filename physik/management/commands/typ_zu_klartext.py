from django.core.management.base import BaseCommand
from physik.models import Aufgabe
import re

class Command(BaseCommand):
    help = "Wandelt den Typ einer Aufgabe (über lfd_nr) in Klartext um"

    def add_arguments(self, parser):
        parser.add_argument(
            "lfd_nr",
            type=str,
            help="Lfd_Nr der Aufgabe (z. B. 'W008_Do')"
        )

    def handle(self, *args, **options):
        lfd_nr = options["lfd_nr"]

        try:
            aufgabe = Aufgabe.objects.get(lfd_nr=lfd_nr)
        except Aufgabe.DoesNotExist:
            self.stdout.write(self.style.ERROR(f"Aufgabe mit lfd_nr '{lfd_nr}' nicht gefunden!"))
            return

        optionen = list(aufgabe.optionen.order_by("position"))
        klartext = self.typ_zu_klartext(aufgabe.typ, aufgabe.loesung, optionen)

        self.stdout.write(self.style.SUCCESS(f"\nAufgabe: {lfd_nr}"))
        self.stdout.write(self.style.SUCCESS(f"Frage: {aufgabe.frage}"))
        self.stdout.write(self.style.SUCCESS(f"Typ: {aufgabe.typ}"))
        self.stdout.write(self.style.SUCCESS(f"Lösung: {aufgabe.loesung}"))
        self.stdout.write(self.style.SUCCESS(f"Optionen:\n" + "\n".join([f"  Position {opt.position}: {opt.text}" for opt in optionen])))
        self.stdout.write(self.style.SUCCESS(f"Klartext: {klartext}\n"))

    def typ_zu_klartext(self, typ, loesung, optionen):
        if not typ:
            return "Kein Typ angegeben."

        klartext = typ

        # Ersetze Operatoren
        klartext = klartext.replace("u", " UND ").replace("o", " ODER ")
        klartext = klartext.replace("f", " ABER NICHT ")
        klartext = klartext.replace("Y", "").replace("Z", "")

        # Index 1 = Lösung
        klartext = klartext.replace("1", f"'{loesung}'")

        # Erstelle Mapping: Position in DB -> Text
        position_to_text = {opt.position: opt.text for opt in optionen}

        # Ersetze die Zahlen im Typ durch die Texte
        for position, text in position_to_text.items():
            klartext = klartext.replace(str(position), f"'{text}'")

        # Aufräumen
        klartext = " ".join(klartext.split())

        return klartext