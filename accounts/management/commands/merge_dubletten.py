from django.core.management.base import BaseCommand
from django.db import transaction
# Passe 'projekte' an den echten Namen deiner App an
from accounts.models import Schule, Profil 

class Command(BaseCommand):
    help = 'Führt bekannte Schul-Dubletten in der Datenbank sauber zusammen'

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("Starte Zusammenführung der Dubletten..."))

        # 1. Ballhaus-Schule zu Martin-Luther-Schule
        self.merge_schools("Martin-Luther-Schule", "Ballhaus-Schule", "DE-HE-4684")

        # 2. Söderblom-Gymnasium Dublette aufräumen
        self.clean_soederblom()

        # 3. Hinterlandschule Standorte aufräumen
        self.clean_hinterland()

    def merge_schools(self, target_name, duplicate_name, school_id):
        try:
            # 'schulname' statt 'name' verwenden
            target_school = Schule.objects.get(schulname__icontains=target_name)
            duplicate_school = Schule.objects.filter(schulname__icontains=duplicate_name).exclude(id=target_school.id).first()
            
            if duplicate_school:
                with transaction.atomic():
                    updated_count = Profil.objects.filter(schule=duplicate_school).update(schule=target_school)
                    duplicate_school.delete()
                    
                    # 'dienststellen_nr' statt 'dienststellennummer' verwenden
                    target_school.dienststellen_nr = school_id
                    target_school.save()
                    
                    self.stdout.write(self.style.SUCCESS(
                        f"✓ '{duplicate_name}' erfolgreich in '{target_name}' integriert ({updated_count} Profile verschoben)."
                    ))
            else:
                target_school.dienststellen_nr = school_id
                target_school.save()
                self.stdout.write(f"i Keine Dublette für '{duplicate_name}' gefunden. ID wurde bei Hauptschule hinterlegt.")
                
        except Schule.DoesNotExist:
            self.stdout.write(self.style.WARNING(f"⚠ Hauptschule mit dem Begriff '{target_name}' wurde nicht gefunden."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"⚠ Fehler bei '{duplicate_name}': {e}"))

    def clean_soederblom(self):
        try:
            s_targets = Schule.objects.filter(schulname__icontains="Söderblom")
            if s_targets.count() > 1:
                master = s_targets.filter(dienststellen_nr="DE-NW-168340").first() or s_targets.first()
                with transaction.atomic():
                    for doublette in s_targets.exclude(id=master.id):
                        Profil.objects.filter(schule=doublette).update(schule=master)
                        doublette.delete()
                    master.dienststellen_nr = "DE-NW-168340"
                    master.save()
                self.stdout.write(self.style.SUCCESS("✓ Söderblom-Gymnasium Dubletten bereinigt."))
            else:
                self.stdout.write("i Keine Dublette beim Söderblom-Gymnasium gefunden.")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"⚠ Fehler bei Söderblom: {e}"))

    def clean_hinterland(self):
        try:
            h_schools = Schule.objects.filter(schulname__icontains="Hinterlandschule")
            if h_schools.count() > 1:
                master = h_schools.first()
                with transaction.atomic():
                    for doublette in h_schools.exclude(id=master.id):
                        Profil.objects.filter(schule=doublette).update(schule=master)
                        doublette.delete()
                    master.dienststellen_nr = "DE-HE-4308"
                    master.save()
                self.stdout.write(self.style.SUCCESS("✓ Hinterlandschule Standorte/Dubletten zusammengeführt."))
            elif h_schools.exists():
                master = h_schools.first()
                master.dienststellen_nr = "DE-HE-4308"
                master.save()
                self.stdout.write(self.style.SUCCESS("✓ Hinterlandschule ID eingetragen (Keine Dublette vorhanden)."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"⚠ Fehler bei Hinterlandschule: {e}"))