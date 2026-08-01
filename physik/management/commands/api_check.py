from django.core.management.base import BaseCommand
from physik.bewertung import check_answer_with_api

class Command(BaseCommand):
    help = "Testet die check_answer_with_api()-Funktion mit manuellen Eingaben"

    def add_arguments(self, parser):
        parser.add_argument(
            "--frage",
            type=str,
            required=True,
            help="Die Frage/Aufgabe (z. B. 'Was ist 2+2?')"
        )
        parser.add_argument(
            "--loesung",
            type=str,
            required=True,
            help="Die erwartete Lösung (z. B. '4')"
        )
        parser.add_argument(
            "--antwort",
            type=str,
            required=True,
            help="Die Schülerantwort (z. B. '4')"
        )

    def handle(self, *args, **options):
        frage = options["frage"]
        loesung = options["loesung"]
        antwort = options["antwort"]

        self.stdout.write(self.style.SUCCESS(f"\nTeste API-Check mit:\n"))
        self.stdout.write(self.style.SUCCESS(f"  Frage:    {frage}"))
        self.stdout.write(self.style.SUCCESS(f"  Lösung:   {loesung}"))
        self.stdout.write(self.style.SUCCESS(f"  Antwort:  {antwort}\n"))

        try:
            ergebnis = check_answer_with_api(frage, loesung, antwort)
            self.stdout.write(self.style.SUCCESS(f"API-Ergebnis: {ergebnis}"))
        except ValueError as e:
            self.stdout.write(self.style.ERROR(f"Konfigurationsfehler: {e}"))
        except RuntimeError as e:
            self.stdout.write(self.style.ERROR(f"API-Fehler: {e}"))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Unbekannter Fehler: {e}"))