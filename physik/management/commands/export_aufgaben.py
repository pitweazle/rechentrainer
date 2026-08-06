import csv
import os
from django.core.management.base import BaseCommand
from physik.models import Aufgabe, AufgabeOption, ThemenBereich, Kapitel

class Command(BaseCommand):
    help = "Exportiert alle Aufgaben inkl. Optionen als CSV für die Bearbeitung in Excel/Calc."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            type=str,
            default="aufgaben_export.csv",
            help="Ausgabedatei (Standard: aufgaben_export.csv)"
        )
        parser.add_argument(
            "--delimiter",
            type=str,
            default=";",
            help="CSV-Trennzeichen (Standard: ;)"
        )

    def handle(self, *args, **options):
        output_file = options["file"]
        delimiter = options["delimiter"]

        # Alle Aufgaben mit zugehörigen Optionen laden
        aufgaben = Aufgabe.objects.all().prefetch_related("optionen", "kapitel", "thema").order_by("lfd_nr")

        if not aufgaben.exists():
            self.stdout.write(self.style.WARNING("Keine Aufgaben gefunden."))
            return

        # CSV-Header definieren (alle Felder von Aufgabe + Optionen 2-9)
        header = [
            "lfd_nr",
            "thema_id",  # ordnung des Themenbereichs
            "thema_name",  # Name des Themenbereichs (zur Info)
            "zeile",  # zeile des Kapitels
            "kapitel",  # Name des Kapitels
            "schwierigkeit",
            "typ",
            "zeichen",
            "frage",
            "loesung",
            "einheit",
            "anmerkung",
            "erklaerung",
            "hilfe",
            "von",  # User-ID des Erstellers
            # Optionen (Position 2-9)
            "2", "3", "4", "5", "6", "7", "8", "9"
        ]

        # CSV schreiben
        with open(output_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=header, delimiter=delimiter)
            writer.writeheader()

            for aufgabe in aufgaben:
                # Optionen als Dict {position: text} vorbereiten
                optionen_dict = {opt.position: opt.text for opt in aufgabe.optionen.all()}

                # Zeile für die CSV erstellen
                row = {
                    "lfd_nr": aufgabe.lfd_nr,
                    "thema_id": aufgabe.thema.ordnung,  # Wichtig für den Import!
                    "thema_name": aufgabe.thema.thema,
                    "zeile": aufgabe.kapitel.zeile,
                    "kapitel": aufgabe.kapitel.kapitel,
                    "schwierigkeit": aufgabe.schwierigkeit,
                    "typ": aufgabe.typ,
                    "zeichen": aufgabe.zeichen,
                    "frage": aufgabe.frage,
                    "loesung": aufgabe.loesung,
                    "einheit": aufgabe.einheit,
                    "anmerkung": aufgabe.anmerkung,
                    "erklaerung": aufgabe.erklaerung,
                    "hilfe": aufgabe.hilfe,
                    "von": aufgabe.von.id if aufgabe.von else "",
                }

                # Optionen hinzufügen (Positionen 2-9)
                for pos in range(2, 10):
                    row[str(pos)] = optionen_dict.get(pos, "")

                writer.writerow(row)

        self.stdout.write(
            self.style.SUCCESS(f"Export erfolgreich! Datei: {os.path.abspath(output_file)}")
        )
        self.stdout.write(
            self.style.NOTICE(
                "Hinweis: Die Spalte 'thema_id' muss die 'ordnung' des Themenbereichs enthalten. "
                "Die Spalten '2'-'9' sind für die Optionen (Position 2-9). "
                "Leere Zellen werden ignoriert."
            )
        )