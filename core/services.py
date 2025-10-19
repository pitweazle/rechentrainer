import math

from datetime import date

from django.db.models import Sum

from .models import Kategorie, Zaehler, Protokoll

from accounts.services import quote_farbe

def durchschnitt_aufgaben(profil, kategorie):
    #if alle:
    protokoll = Protokoll.objects.filter(profil=profil)
    # else:
    #     protokoll = Protokoll.objects.filter(profil=profil, sj=profil.sj, hj=profil.hj)
    zaehler = Zaehler.objects.filter(profil=profil)
    temp = protokoll.aggregate(Sum('richtig'))['richtig__sum']
    richtig_gesamt = temp if temp else  0
    anzahl = zaehler.filter(sj = profil.sj, hj = profil.hj).count()                             # Anzahl der, in diesem Hj bearbeiteten Kategorien                                                       
    zaehler = zaehler.filter(kategorie = kategorie).first()
    fehler_ab = zaehler.fehler_ab
    protokoll = protokoll.filter(kategorie = kategorie, start__gt=fehler_ab)
    temp = protokoll.aggregate(Sum('falsch'))['falsch__sum']
    fehler_kat = temp if temp else  0
    richtig_gesamt = temp if temp else  0
    if anzahl == 0:
        durchschnitt = 0
    else:
        durchschnitt = int(richtig_gesamt/anzahl)
    return durchschnitt, richtig_gesamt, fehler_kat

def soll_berechnung(sj, hj, jg, aufgaben_pro_woche, startdatum):
    d0 = date(sj//100+2000,7,24)
    d1 = date.today()
    delta = d1 - d0
    aufg1hj = [1,1,1,1,2,3,4,5,6,7,8,8,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23]           # weniger Aufgaben am Anfang und keine in den Ferien - maximal 1600 (siehe unten)
    aufg2hj = [1,1,2,3,4,5,6,7,8,9,10,10,10,11,12,13,14,15,16,17,18,19,20,21,22,23, 24,25, 26]   
    schulwoche = delta.days//7                                                                  # Schulwoche wird benötigt um Anzuzeigen welche Kategorien bearbeitet werden müssen
    if schulwoche < 0: 
        schulwoche = 0  
    # wenn die Lerngruppe nach dem Beginn des Halbjahres angelegt wurde, werden von den Sollaufgaben entsprechend abgezogen - ebenso, wenn keine Lerngruppe verknüpft ist, entsprechend mit der Registrierung
    # profil_gruppe = profil.gruppe
    # if profil_gruppe:
    #     startdatum = profil.gruppe.erstellt_am
    # else:
    #     startdatum = profil.user.date_joined
    if hj == 2:
        zweites_hj = (sj%100+2000)
        d2 = date(zweites_hj,1,24)
        delta2 = d1 - d2
        woche_halbjahr =  delta2.days//7                                                        # wird benötigt um auszurechnen, wieviele Aufgaben gerechnet werden sollten
        try:
            spaeter = ((startdatum.date()-d2).days)//7
        except:
            spaeter = ((startdatum-d2).days)//7
    else:
        woche_halbjahr = schulwoche
        try:
            spaeter = (startdatum.date() - d0).days//7 
        except:       
            spaeter = (startdatum - d0).days//7
    if spaeter >= woche_halbjahr:
        spaeter = 0
    if spaeter < 0:
        spaeter = 0
    if woche_halbjahr <= 0:
        woche_halbjahr = 0
        spaeter = 0
    try:
        if hj == 2:
            soll_hj = aufg2hj[woche_halbjahr] - aufg2hj[spaeter]
        else:
            soll_hj = aufg1hj[woche_halbjahr] - aufg1hj[spaeter]
    except:
        soll_hj = 1
    soll_hj = int(soll_hj * aufgaben_pro_woche)                                                 # ist die Anzahl der Aufgaben, die in dieser Woche gerechnet worden sein müssten (pro Schulwoche und Jahrgang des Users 10 - also z.B. 70 pro Woche im Jahrgang 7)
    if soll_hj > 1600:
        soll_hj = 1600
    pflicht_kat = Kategorie.objects.filter(start_sw__lte= schulwoche, start_jg = jg) | Kategorie.objects.filter(start_jg__lt = jg)
    pflicht_kat = pflicht_kat.count()
    if pflicht_kat > 0:
        soll_kat = int(soll_hj/pflicht_kat)
    else:
        soll_kat = 0                 
    if soll_kat < 10:
        soll_kat = 10
    return schulwoche, woche_halbjahr, soll_hj, soll_kat, pflicht_kat

def bewertung_kat(soll_kat, richtig, falsch, lsg, abbr, stufe):
    prozent_kat = 0 if soll_kat == 0 else richtig/soll_kat*100
    if prozent_kat > 50:
        prozent_kat = (prozent_kat+(richtig-falsch-lsg-abbr)/richtig*100)/2
    if prozent_kat > 110:
        prozent_kat = 110
    if prozent_kat < 0:
        prozent_kat = 0
    prozent_farbe = quote_farbe(prozent_kat,100-prozent_kat,0.5)
    return prozent_farbe, prozent_kat 

def bewertung_hj(prozent_summe, pflicht_kat, stufe, keine5=True):                            # Bewertung + Note für das Halbjahr
    prozent_summe = int(prozent_summe/pflicht_kat)                              # addiert alle Prozentwerte und bildet den Durchschnitt (aus)
    prozent_summe_farbe = quote_farbe(prozent_summe,100-prozent_summe,0.5)
    note = 6 if prozent_summe < 25 else 7-((prozent_summe-stufe%2*5)//15)       # für E-Kurs 1,2,3,4,5 bei 95,80,65,50% für G-Kurs entsprechende Note mit 5% weniger
    str_note = str(note)
    plusminus = (prozent_summe+3-stufe%2*5)%15                                  # + oder - bei 3% mehr oder weniger
    if plusminus in range (3,6):
        str_note = str(note)+"-"
    if plusminus in range (0,3):
        str_note = str(note)+"+"
    if note > 4 and keine5:
         str_note = '-'
    return prozent_summe_farbe, prozent_summe, str_note 

def erstelle_reihenfolge(typ_anf: int, typ_end: int, length: int = 15, start_after=None):
    """
    Baut eine Sequenz von Typen aus [typ_anf..typ_end] mit:
      - keinem direkten Duplikat,
      - Start NICHT == start_after (falls >1 Typ),
      - zyklischer Wiederholung bis 'length'.
    """
    # Normalisieren
    if typ_anf > typ_end:
        typ_anf, typ_end = typ_end, typ_anf

    base = list(range(typ_anf, typ_end + 1))
    if not base:
        return []
    if len(base) == 1:
        return base * length  # nur ein Typ möglich

    # So rotieren, dass der erste nicht start_after ist (wenn möglich)
    if start_after in base:
        i = (base.index(start_after) + 1) % len(base)
        base = base[i:] + base[:i]

    # Auf Länge bringen (einfach ganze Zyklen wiederholen)
    reps = math.ceil(length / len(base))
    seq = (base * reps)[:length]

    # Sicherheitsnetz: falls durch externe Änderungen doch mal ein Doppel entsteht
    for j in range(1, len(seq)):
        if seq[j] == seq[j-1] and len(base) > 1:
            # mit nächstem Element tauschen (zyklisch)
            k = (j + 1) % len(seq)
            seq[j], seq[k] = seq[k], seq[j]
    return seq