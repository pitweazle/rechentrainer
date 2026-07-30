from django.core.management.base import BaseCommand
from django.db.models import Sum, Min
from accounts.models import Profil
from core.models import Protokoll, EwigeBestenliste

class Command(BaseCommand):
    help = 'Einmaliger Migrations-Befehl zur Verknüpfung der alten Bestenliste mit Profil-IDs.'

    def handle(self, *args, **options):
        # 1. Einmalige Verknüpfung für alle Einträge, die noch keine profil_id haben
        eintraege_ohne_id = EwigeBestenliste.objects.filter(profil_id__isnull=True)
        if eintraege_ohne_id.exists():
            for eintrag in eintraege_ohne_id:
                for profil in Profil.objects.all():
                    p_name = f"{profil.vorname} {profil.nachname}".strip()
                    if p_name == eintrag.name:
                        eintrag.profil_id = profil.id
                        eintrag.save()
                        break
            self.stdout.write(self.style.SUCCESS("Alte Bestenliste erfolgreich mit Profil-IDs verknüpft!"))

        # 2. Reguläres Update und Top-10-Berechnung (gleiche Logik wie danach)
        protokoll_summen = {
            item['profil_id']: item['punkte'] 
            for item in Protokoll.objects.values('profil_id').annotate(punkte=Sum('richtig'))
        }
        protokoll_daten = {
            item['profil_id']: item['start_datum'] 
            for item in Protokoll.objects.values('profil_id').annotate(start_datum=Min('start'))
        }

        live_daten = {}
        for profil in Profil.objects.select_related('gruppe__lehrer__profil').all():
            hist_pts = profil.historische_aufgaben_richtig or 0
            aktuelle_pts = protokoll_summen.get(profil.id, 0)
            gesamt = hist_pts + aktuelle_pts
            
            if gesamt > 0:
                schule_name = "Keine Schule"
                lehrer_name = "Kein Lehrer"
                if profil.gruppe and hasattr(profil.gruppe, 'lehrer') and profil.gruppe.lehrer:
                    lehrer = profil.gruppe.lehrer
                    if hasattr(lehrer, 'profil'):
                        lehrer_name = getattr(lehrer.profil, 'nachname', "Kein Lehrer")
                        if hasattr(lehrer.profil, 'schule') and lehrer.profil.schule:
                            schule_name = lehrer.profil.schule.schulname

                vollstaendiger_name = f"{profil.vorname} {profil.nachname}".strip()
                bestes_datum = protokoll_daten.get(profil.id) or (profil.erstellt_am if hasattr(profil, 'erstellt_am') and profil.erstellt_am else profil.user.date_joined)

                live_daten[profil.id] = {
                    'profil_id': profil.id, 'name': vollstaendiger_name,
                    'lehrer': lehrer_name, 'schule': schule_name,
                    'punkte': gesamt, 'letztes_datum': bestes_datum
                }

        archiv_daten = { e.profil_id: e for e in EwigeBestenliste.objects.exclude(profil_id__isnull=True) }
        master_pool = {}
        
        for p_id, daten in live_daten.items():
            if p_id in archiv_daten:
                eintrag = archiv_daten[p_id]
                if daten['punkte'] > eintrag.punkte:
                    eintrag.punkte = daten['punkte']
                    eintrag.letztes_datum = daten['letztes_datum']
                eintrag.lehrer = daten['lehrer']
                eintrag.schule = daten['schule']
                eintrag.name = daten['name']
                master_pool[p_id] = eintrag
            else:
                master_pool[p_id] = EwigeBestenliste(
                    profil_id=daten['profil_id'], name=daten['name'],
                    lehrer=daten['lehrer'], schule=daten['schule'],
                    punkte=daten['punkte'], letztes_datum=daten['letztes_datum']
                )

        alle_schueler = list(master_pool.values())
        alle_schueler.sort(key=lambda x: x.punkte, reverse=True)
        top_10 = alle_schueler[:10]

        EwigeBestenliste.objects.all().delete()
        for s in top_10:
            s.pk = None
            s.save()

        self.stdout.write(self.style.SUCCESS("Bestenliste erfolgreich aktualisiert und migriert!"))