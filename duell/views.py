import random
from py_expression_eval import Parser

from decimal import *

from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.http import HttpResponse 

from django.db.models import Count 

from accounts.models import Profil, Lerngruppe
from accounts.views import stufe_aus_jg

from core.models import Kategorie, Auswahl, Protokoll, Zaehler 
from core.forms import AufgabeFormZahl, AufgabeFormStr
from core.views import format_zahl, aufgaben, kontrolle

from .models import  Duellant, Duell_Protokoll, Duell_Eingabe
from .forms import Duellant_Aendern_Form, Duell_AuswahlForm, AufgabeFormTab, DuellProtokollFilter

# das Rechenduell
def duell_uebersicht(req, gruppe_id):
    gruppe = get_object_or_404(Lerngruppe, pk=gruppe_id)
    if gruppe.lehrer != req.user and not req.user.is_superuser:
        return HttpResponse("Zugriff verweigert")
    profil = get_object_or_404(Profil, user=req.user)
    profil.duell_gruppe = gruppe_id
    profil.save() 
    duellanten = Duellant.objects.filter(profil__gruppe=gruppe_id)
    if duellanten.count() == 0:                         # löscht die gespeicherten Aufgabennummern der einzelnen Kategorien der Lehrkraft
        zaehler = Zaehler.objects.filter(user = req.user.profil)
        for kategorie in zaehler:
            kategorie.aufgnr = 0
            kategorie.save()
    for duellant in duellanten:
        duellant.punkte +=duellant.punkte_spiel
        duellant.punkte_spiel = 0
        if duellant.spiele != 0:
            duellant.pps = duellant.punkte/duellant.spiele
        duellant.save()
    schueler_liste = Profil.objects.filter(gruppe=gruppe).order_by("user__profil__vorname")
    for schueler in schueler_liste:
        duellant, created = Duellant.objects.get_or_create(profil = schueler)
        if created:
            duellant.name = schueler.vorname
            duellant.save()
    dubletten = duellanten.values('name').annotate(dubletten=Count('name')).filter(dubletten__gt=1)
    dubletten_liste = []
    if not dubletten:
        pass
    else:
        for dublette in dubletten:
            dubletten_liste.append(dublette["name"])
    leerstellen_liste = []
    for duellant in duellanten:
        if " " in duellant.name:
            leerstellen_liste.append(duellant.name)
    duellanten = duellanten.filter(profil__gruppe = gruppe).order_by("liga", "platz", "profil")
    duell_rang(gruppe.id)
    if req.method == 'POST': 
        IDs = list(req.POST.getlist('ID'))
        for duellant in duellanten:
            duellant.abwesend = True if str(duellant.id) in IDs else False
            duellant.save()
    req.session['gruppe_id'] = gruppe_id  
    context={'gruppe_id': gruppe_id, 'gruppe': gruppe, 'duellanten': duellanten, 'dubletten_liste': ", ".join(dubletten_liste), 'leerstellen_liste': ", ".join(leerstellen_liste),'titel': "Schülerdaten ändern"} 
    return render(req, 'duell_uebersicht.html', context)

def duell_start(req, gruppe_id):
    gruppe = Lerngruppe.objects.get(pk = req.session.get('gruppe_id'))
    if gruppe.lehrer != req.user and not req.user.is_superuser:
        return HttpResponse("Zugriff verweigert") 
    kategorien = Kategorie.objects.all().order_by('zeile')
    zaehler = Zaehler.objects.filter(user = req.user.profil)
    for item in zaehler:
        item.optionen_text = ""
        item.save()
    context={'gruppe': gruppe, 'kategorien': kategorien} 
    return render(req, 'duell_start.html', context)

def duellant_aendern(req, gruppe_id, duellant_id):
    gruppe = get_object_or_404(Lerngruppe, pk=gruppe_id)
    if gruppe.lehrer != req.user:
        return HttpResponse("Zugriff verweigert")
    duellanten = Duellant.objects.filter(profil__gruppe = gruppe_id).order_by("liga", "platz", "profil")
    duellant = Duellant.objects.get(pk = duellant_id)
    if duellant.profil.gruppe.lehrer != req.user and not req.user.is_superuser:
        return HttpResponse("Zugriff verweigert") 
    if req.method == 'POST':
        form = Duellant_Aendern_Form(req.POST, instance=duellant)
        if  form.is_valid():
            form.save() 
            if duellant.spiele != 0:
                duellant.pps = duellant.punkte/duellant.spiele
                duellant.save()             
        return duell_uebersicht(req, gruppe_id)
    form = Duellant_Aendern_Form(instance=duellant)
    return render(req, 'duellant_aendern.html', {'gruppe_id': gruppe_id, 'duellanten': duellanten, 'duellant': duellant, 'form': form, 'edit':True})

def duell_aufgabe(req, slug):
    gruppe = Lerngruppe.objects.get(pk = req.session.get('gruppe_id'))
    if gruppe.lehrer != req.user:
        return HttpResponse("Zugriff verweigert")
    kategorie = get_object_or_404(Kategorie, slug = slug)
    user = req.user.profil
    duellant_1, duellant_2 = sub_auslosen(gruppe.id)
    zaehler, created = Zaehler.objects.get_or_create(user = user, kategorie = kategorie)
    if zaehler.aufgnr == 0:     # Das ist jeweils die erste Aufgabe von 10
        zaehler.aufgnr = 1
    #hier wird die entsprechende Funktion aufgerufen und festgelegt, aus welchem Bereich (Typ) Aufgaben erzeugt werden
    #zunächst wird überprüft, ob für diese kategorie Einträge bei "Optionen" vorhanden sind:
    if not zaehler.optionen_text :  
        return redirect('duell_optionen', slug)
    #!!!!!!!! hier wird dann die nächste Aufgabe erzeugt: 
    if kategorie.slug == "sachaufgaben":
        try:  
            user.voreinst["sachaufg"] = user.voreinst["sachaufg"] + 1
        except:                                       
            user.voreinst.update({"sachaufg" : random.randint(1,20)})
        user.save()
        typ_anf = user.voreinst["sachaufg"]
    else:
        typ_anf = zaehler.typ_anf  
    typ_end = zaehler.typ_end  
    jg = gruppe.jg          
    stufe=(stufe_aus_jg(gruppe.jg))
    #unter Umständen gibt es auch spezielle Aufgaben für A-Kurs und Gymnasium - dazu wird hier die Stufe um 0,2 hochgesetzt
    if kategorie.name in ("Prozentrechnung","Bruchteile"):
        if user.kurs == "A" or user.kurs == "Y":
            stufe = stufe + 0.2
    typ, typ2, titel, text, pro_text, frage, variable, einheit, anmerkung, lsg, hilfe_id, ergebnis, parameter = aufgaben(kategorie.zeile, jg = jg, stufe = stufe, aufgnr = zaehler.aufgnr, typ_anf = typ_anf, typ_end = typ_end, optionen = "") 
    if kategorie.slug == "sachaufgaben":
        user.voreinst["sachaufg"] = typ
        user.save()
    if not titel:
        titel = kategorie.name
    text = text.format(*variable)
    if pro_text != "" :
        pro_text = pro_text.format(*variable)
    frage = frage.format(*variable)
    protokoll = Protokoll.objects.create(
        user = user, titel = titel, sj = user.sj, hj = user.hj, kategorie = kategorie, text = text, pro_text = pro_text, variable = variable, frage = frage, einheit = einheit, 
        anmerkung = anmerkung, wert = ergebnis, loesung = lsg, hilfe_id = hilfe_id, parameter = parameter, wertung = "Duell", typ = typ, typ2 = typ2, aufgnr = zaehler.aufgnr,        
    )                                                                   #Protokoll wird erstellt
    duell_protokoll = Duell_Protokoll.objects.create(
        protokoll = protokoll, gruppe = gruppe, duellant_1 = duellant_1, duellant_2 = duellant_2 
    ) 
    #Jenachdem, ob ein Wert oder ein Text erwartet wird:
    if "tab" in protokoll.parameter["name"]:
        # if "term" in protokoll.parameter["name"]:
        #     form = DuellFormTerm(req.POST)
        # else:
        form = AufgabeFormTab(req.POST)
    else:
        if protokoll.wert:
            form = AufgabeFormZahl(req.POST)
        #wenn in den Aufgaben erg=None:
        else:
            form = AufgabeFormStr(req.POST)
    if duellant_1.liga != duellant_2.liga:
        meldung = "Aufstiegsduell:"
    elif duellant_1.aufsteiger != duellant_2.aufsteiger:
        meldung = 'Relegationsspiel'
    else:
        meldung = ""
    req.session['protokoll_id'] = protokoll.id  
    req.session['duell_id'] = duell_protokoll.id 
    aufsteiger_1 = "↑" if duell_protokoll.duellant_1.aufsteiger else ""
    aufsteiger_2 = "↑" if duell_protokoll.duellant_2.aufsteiger else "" 
    context = dict(protokoll = protokoll,  duell_protokoll = duell_protokoll, parameter = parameter,   
        farbe_1 = "null", farbe_2 = "null", aufsteiger_1 = aufsteiger_1, aufsteiger_2 = aufsteiger_2, 
        form = form, message_unten = anmerkung, meldung = meldung, neu = "neu")
    return render(req, 'aufgabe_duell.html', context)

def duell_optionen(req, slug):
    gruppe = Lerngruppe.objects.get(pk = req.session.get('gruppe_id'))
    jg = gruppe.jg          
    stufe=(stufe_aus_jg(gruppe.jg))
    kategorie = get_object_or_404(Kategorie, slug = slug)
    form = Duell_AuswahlForm(kategorie = kategorie)
    user = req.user  
    if req.method == 'POST':
        form = Duell_AuswahlForm(req.POST, kategorie = kategorie, jg=jg, stufe=stufe)
        if form.is_valid():
            optionen_text = ';'.join(map(str, form.cleaned_data['optionen']))
            if optionen_text == "":
                optionen_text = "keine"
        else:
            optionen_text = "keine"  
    else:
        form = Duell_AuswahlForm(kategorie=kategorie, jg=jg, stufe=stufe)
        anzahl = kategorie.auswahl_set.all().count()
        if anzahl>0:
            anzahl = Auswahl.objects.filter(bis_jg__gte = jg, bis_stufe__gte = stufe, kategorie = kategorie).count()
            if anzahl>0:
                return render(req, 'duell_optionen.html', {'kategorie': kategorie, 'auswahl_form':form})
            else:
                optionen_text = "keine"    
        else:
            optionen_text = "keine"
    zaehler = get_object_or_404(Zaehler, kategorie = kategorie, user = user.profil)
    zaehler.optionen_text = optionen_text       
    typ_anf, typ_end = aufgaben(kategorie.zeile, jg = jg, stufe = stufe, optionen = zaehler.optionen_text)
    zaehler.typ_anf = typ_anf
    zaehler.typ_end = typ_end
    zaehler.save()
    return redirect('duell_aufgabe', slug)

def sub_auslosen(gruppe_id):
    duellanten = Duellant.objects.filter(profil__gruppe=gruppe_id)
    duellanten = duellanten.exclude(abwesend=True).order_by("-spiele")
    duellanten_liste = []
    for duellant in duellanten:
        duellanten_liste.append(duellant.id)
    duellant_1 = duellanten.last()
    duellant_1.spiele +=1
    duellant_1.punkte_spiel = 0
    duellant_1.save()
    duellanten = duellanten.exclude(name=duellant_1.name)
    duellanten = duellanten.order_by("liga","-spiele")
    duellanten_liste = []
    if duellant_1.liga == "A":                                            # wenn in der oberste Liga 
        duellanten = duellanten.filter(liga="A")
        for duellant in duellanten:
            duellanten_liste.append(duellant.id)
    else:
        liga_B = duellanten.filter(liga="B").count()
        liga_C = duellanten.filter(liga="C").count()
        if liga_B + liga_C == 0:                                        # es gibt nur eine Liga
            exit
        liga_A = duellanten.filter(liga="A").count()
        for duellant in duellanten:
            duellanten_liste.append(duellant.id)
       
        if duellant_1.liga == "C":
            duellanten_liste = duellanten_liste[-(liga_C+2):]           # die Kandidaten in Liga C plus zwei in Liga B
        else:
            duellanten_liste = duellanten_liste    # die Kandidaten in Liga B plus zwei in Liga A ohne Liga C
    duellant_2 = duellanten.get(id = random.choice(duellanten_liste))
    duellant_2.spiele +=1
    duellant_2.punkte_spiel = 0
    duellant_2.save()
    return  duellant_1, duellant_2 

def duell_rang(gruppe_id):
    duellanten = Duellant.objects.filter(profil__gruppe=gruppe_id)
    for duellant in duellanten:
        duellant.punkte +=duellant.punkte_spiel
        duellant.punkte_spiel = 0
        if duellant.spiele != 0:
            duellant.pps = duellant.punkte/duellant.spiele
        duellant.save()
    if duellanten.filter(spiele=0, abwesend=False).count()>0:
        exit
    else:
        for liga in ["A","B","C"]:
            duellanten_liga = duellanten.filter(liga=liga).order_by("-pps","-spiele")
            rang = 0
            pps_speicher = 99
            platz_speicher = 99
            spiele_speicher = 99
            for duellant in duellanten_liga:
                rang +=1
                if duellant.pps == pps_speicher: 
                    if duellant.pps > 0:
                        if duellant.spiele == spiele_speicher:
                            duellant.platz = platz_speicher
                        else:
                            duellant.platz=rang
                    else:
                        duellant.platz = platz_speicher
                else:
                    duellant.platz=rang
                pps_speicher = duellant.pps
                platz_speicher = duellant.platz
                spiele_speicher = duellant.spiele
                duellant.save()

def duell_loesung(req):
    duell_protokoll = Duell_Protokoll.objects.get(pk = req.session.get('duell_id'))
    #gruppe = get_object_or_404(Lerngruppe, pk=duell_protokoll.gruppe_id)
    protokoll = Protokoll.objects.get(pk = req.session.get('protokoll_id'))
    if "tab" in protokoll.parameter["name"]:                            # für Wertetabellen
        protokoll.loesung = [protokoll.parameter['y5']]
        #protokoll.wert = round(round(parser.parse(protokoll.parameter['y5'].replace(",",".").replace(":","/")).evaluate({}),3),3)
        protokoll.save()
    text = ""
    try:
        if isinstance(protokoll.loesung[0], list):
            text = "; ".join(protokoll.loesung[0]).replace(".",",")
        else:
            text = protokoll.loesung[0]
    except:
        text = protokoll.loesung
    messages.info(req, f'Lösung: {text}') 
    farbe_1 = farbe(duell_protokoll.duellant_1.punkte_spiel)
    farbe_2 = farbe(duell_protokoll.duellant_2.punkte_spiel)
    context = dict(protokoll = protokoll, duell_protokoll = duell_protokoll, parameter = protokoll.parameter,   
        farbe_1 = farbe_1, farbe_2 = farbe_2, richtig = protokoll.loesung[0],
        message_unten = protokoll.anmerkung, lsg = True)
    return render(req, 'aufgabe_duell.html', context)
 
def sub_punkte(req, duell_protokoll, duellant, duellant_nr, eingabe, punkte, beide = False):
    protokoll = Protokoll.objects.get(pk = req.session.get('protokoll_id'))
    duellant.punkte_spiel += punkte
    duellant.save()
    protokoll.richtig = punkte 
    protokoll.save()
    if beide != "Zweiter":
        duell_eingabe = Duell_Eingabe.objects.create(duell_protokoll = duell_protokoll)
        duell_eingabe.eingabe = eingabe
        duell_eingabe.punkte = punkte
        duell_eingabe.duellant_nr = duellant_nr
        if beide:
            duell_eingabe.anmerkung = "gleich schnell"
        else:
            duell_eingabe.anmerkung = duellant.name
        duell_eingabe.save()
        return duell_eingabe

def sub_eingabe(req, duellant, beide, punkte):
    duell_protokoll = Duell_Protokoll.objects.get(protokoll = req.session.get('protokoll_id'))
    if beide:
        duellant = duell_protokoll.duellant_1              
        eintragz = sub_punkte(req, duell_protokoll, duellant, 2, punkte )        # schreibt Punkte für 1 gut und gibt 
        duellant = duell_protokoll.duellant_2
        doppelt = punkte(req, duell_protokoll, duellant, 2, punkte )             # schreibt Punkte für 1 gut
        doppelt.delete()                                                         # löscht doppelten Eintrag in Duell_Eingabe
        doppelt.save()
    else:
        duellant = Duellant.objects.get(name=duellant.name)
        if duellant.name == duell_protokoll.duellant_1.name:
            duellant_nr = 1
        else:
            duellant_nr = 3
        eintrag = sub_punkte(req, duell_protokoll, duellant, duellant_nr, 1 )
    return eintrag

def duell_kontrolle(req):
    meldung = ""
    gruppe = Lerngruppe.objects.get(pk = req.session.get('gruppe_id'))
    if gruppe.lehrer != req.user:
        return HttpResponse("Zugriff verweigert")
    protokoll = Protokoll.objects.get(pk = req.session.get('protokoll_id'))
    protokoll.versuche += 1
    duell_protokoll = Duell_Protokoll.objects.get(pk = req.session.get('duell_id'))
    zaehler = Zaehler.objects.get(user = req.user.profil, kategorie = protokoll.kategorie)
    context = dict()
    #wenn in den Aufgaben in "erg" eine Zahl steht
    if "tab" in protokoll.parameter["name"]:
        # if "term" in protokoll.parameter["name"]:
        #     form = AufgabeFormTerm(req.POST)
        # else:
        form = AufgabeFormTab(req.POST)
    else:
        if protokoll.wert:
            form = AufgabeFormZahl(req.POST)
        #wenn in den Aufgaben erg=None:
        else:
            form = AufgabeFormStr(req.POST)
    #Aufgabe beantwortet
    if form.is_valid():
        # zunächst Einträge im Protokoll:
        if "tab" in protokoll.parameter["name"]:                            # für Wertetabellen
            eingabe = pro_eingabe = str(form.cleaned_data['y5'])
            parser = Parser()
            eingabe=round(round(parser.parse(eingabe.replace(",",".").replace(":","/")).evaluate({}),3),3)
            protokoll.loesung = protokoll.parameter['y5']
            print("Tab: ", protokoll.parameter)
            if isinstance(protokoll.parameter['y5'], str):
               protokoll.parameter['y5'] = format_zahl(protokoll.parameter['y5'],2).replace(",",".")
               protokoll.save()
               #protokoll.wert = round(round(parser.parse(protokoll.parameter['y5'].replace(",",".").replace(":","/")).evaluate({}),3),3)
            protokoll.wert = protokoll.parameter['y5']
            protokoll.save()
        else:
            eingabe = pro_eingabe = form.cleaned_data['eingabe']
        req.session['eingabe'] = duell_protokoll.id
        #protokoll.eingabe = pro_eingabe
        protokoll.abbr = False
        protokoll.end = timezone.now()
        protokoll.save()
        #hier wird die Eingabe überprüft:
        wertung, rueckmeldung = kontrolle(eingabe, protokoll.wert, protokoll.loesung, protokoll.id)
        richtig = wertung
        duellant_name = req.POST.get('duellant')
        beide = True if duellant_name == "gleich schnell" else False
        #wenn Eingabe richtig:
        if wertung > 0  :
            if "enauer" in rueckmeldung:
                rueckmeldung = "Die letzte Aufgabe war fast richtig!"+ rueckmeldung
            else:
                rueckmeldung = "Die letzte Aufgabe war richtig!"+ rueckmeldung
            punkte = 1
            if zaehler.aufgnr == 0:     # Das ist jeweils die erste Aufgabe von 10
                zaehler.aufgnr = 1
            zaehler.aufgnr += 1
            zaehler.save()
            if zaehler.aufgnr > 10:
                zaehler.aufgnr = 0
                zaehler.save()                
                return redirect('duell_uebersicht', gruppe.id)
            if beide:
                duellant = duell_protokoll.duellant_1
                sub_punkte(req, duell_protokoll, duellant, 2, eingabe, punkte, "Erster" )
                duellant = duell_protokoll.duellant_2
                sub_punkte(req, duell_protokoll, duellant, 2, eingabe, punkte, "Zweiter" )
            else: 
                duellant = Duellant.objects.get(name=duellant_name)
                if duellant.name == duell_protokoll.duellant_1.name:
                    duellant_nr = 1
                else:
                    duellant_nr = 3
                wechsel = sub_punkte(req, duell_protokoll, duellant, duellant_nr, eingabe, punkte, False )
                if duell_protokoll.duellant_1.liga != duell_protokoll.duellant_2.liga:                          # zwei verschiedene Ligen
                    if duellant.liga > duell_protokoll.duellant_2.liga:
                        meldung = auf_abstieg(duellant, duell_protokoll.duellant_2)
                        rueckmeldung += "<br>" + meldung
                    elif duellant.liga > duell_protokoll.duellant_1.liga:
                        meldung = auf_abstieg(duellant, duell_protokoll.duellant_1)
                        rueckmeldung += "<br>" + meldung
                    wechsel.anmerkung=meldung
                    wechsel.save()
                else:
                    if duell_protokoll.duellant_1.aufsteiger != duell_protokoll.duellant_2.aufsteiger:          # einer der Duellanten ist Aufsteiger
                    # if (duell_protokoll.duellant_1.aufsteiger or duell_protokoll.duellant_2.aufsteiger) and not (duell_protokoll.duellant_1.aufsteiger and duell_protokoll.duellant_2.aufsteiger):
                        if duell_protokoll.duellant_1.aufsteiger and duellant == duell_protokoll.duellant_2:    # duellant_1 ist aufsteiger, hat verloren und steigt wieder ab
                            meldung = abstieg(duell_protokoll.duellant_1)
                            rueckmeldung += "<br>" + meldung
                        if duell_protokoll.duellant_2.aufsteiger and duellant == duell_protokoll.duellant_1:    # duellant_2 ist aufsteiger, hat verloren und steigt wieder ab
                            meldung = abstieg(duell_protokoll.duellant_2)
                            rueckmeldung += "<br>" + meldung
                        wechsel.anmerkung=meldung
                        wechsel.save()
            messages.info(req, f'{rueckmeldung}')
            context['richtig'] = eingabe
        #wenn Aufgabe falsch:
        else:
            if wertung < 0:
                punkte = Decimal(-0.5)
                messages.info(req, f'Die letzte Aufgabe war leider falsch! Versuche: {protokoll.versuche}')#, {msg}') 
            else:
                if not "tab" in protokoll.parameter["name"]:
                    messages.info(req, f'{rueckmeldung}')   #gibt eine Rückmeldung wenn "indiv" bei Lösung steht 
                punkte = Decimal(-0.5)
            if beide:
                duellant = duell_protokoll.duellant_1
                sub_punkte(req, duell_protokoll, duellant, 2, eingabe, punkte, "Erster" )
                duellant = duell_protokoll.duellant_2
                sub_punkte(req, duell_protokoll, duellant, 2, eingabe, punkte, "Zweiter" )
            else:
                duellant = Duellant.objects.get(name=duellant_name)
                if duellant.name == duell_protokoll.duellant_1.name:
                    duellant_nr = 1
                else:
                    duellant_nr = 3
                wechsel = sub_punkte(req, duell_protokoll, duellant, duellant_nr, eingabe, punkte )
            context['falsch'] = eingabe
    farbe_1 = farbe(duell_protokoll.duellant_1.punkte_spiel)
    farbe_2 = farbe(duell_protokoll.duellant_2.punkte_spiel)
    context.update(protokoll = protokoll, duell_protokoll = duell_protokoll, parameter = protokoll.parameter,   
        farbe_1 = farbe_1, farbe_2 = farbe_2, 
        form = form,    message_unten = protokoll.anmerkung)
    return render(req, 'aufgabe_duell.html', context)

def auf_abstieg(aufsteiger, absteiger):
    stringwert = ord(aufsteiger.liga)
    aufsteiger.liga = chr(stringwert-1)
    aufsteiger.aufsteiger = True
    aufsteiger.save()
    stringwert = ord(absteiger.liga)
    absteiger.liga = chr(stringwert+1)
    absteiger.aufsteiger = False
    absteiger.save()
    meldung = aufsteiger.name + " steigt auf - " + absteiger.name + " steigt ab"
    return meldung  

def abstieg(absteiger):
    stringwert = ord(absteiger.liga)
    absteiger.liga = chr(stringwert+1)
    absteiger.aufsteiger = False
    absteiger.save()
    meldung = absteiger.name + " steigt wieder ab"
    return meldung  

def farbe(punkte):
    if punkte == 0:
        farbe = "null" 
    elif punkte > 0:
        farbe = "plus" 
    else:
        farbe = "minus"
    return farbe

def duellant_edit(req, duellant_id, punkte):
    duell_protokoll = Duell_Protokoll.objects.get(pk = req.session.get('duell_id'))
    gruppe = get_object_or_404(Lerngruppe, pk=duell_protokoll.gruppe_id)
    if gruppe.lehrer != req.user:
        return HttpResponse("Zugriff verweigert")
    duellant = Duellant.objects.get(id=duellant_id)
    protokoll = Protokoll.objects.get(pk = req.session.get('protokoll_id'))
    #zaehler = Zaehler.objects.get(pk = req.session.get('zaehler_id'))
    duell_eingabe = Duell_Eingabe.objects.create(duell_protokoll = duell_protokoll) 
    if punkte == "plus":
        duellant.punkte_spiel +=Decimal(0.5)
        duell_eingabe.punkte = Decimal(0.5)
    elif punkte == "minus":
        duellant.punkte_spiel -=Decimal(0.5)
        duell_eingabe.punkte = -Decimal(0.5)
    duellant.save()
    duell_eingabe.anmerkung = "edit"
    duell_eingabe.save()
    farbe_1 = farbe(duell_protokoll.duellant_1.punkte_spiel)
    farbe_2 = farbe(duell_protokoll.duellant_2.punkte_spiel)
    if protokoll.wert:
        form = AufgabeFormZahl(req.POST)
    else:
        form = AufgabeFormStr(req.POST)
    context = dict(protokoll = protokoll, duell_protokoll = duell_protokoll, parameter = protokoll.parameter,   
        farbe_1 = farbe_1, farbe_2 = farbe_2, 
        message_unten = protokoll.anmerkung, edit = True, richtig = protokoll.loesung[0])
    return render(req, 'aufgabe_duell.html', context)

def neu_auslosen(req, mit):
    gruppe = Lerngruppe.objects.get(pk = req.session.get('gruppe_id'))
    if gruppe.lehrer != req.user:
        return HttpResponse("Zugriff verweigert")
    duell_rang(gruppe.id)
    protokoll = Protokoll.objects.get(pk = req.session.get('protokoll_id'))
    duell_protokoll = Duell_Protokoll.objects.get(pk = req.session.get('duell_id'))
    duell_eingabe = Duell_Eingabe.objects.create(duell_protokoll = duell_protokoll)
    if mit == "mit":
        duell_protokoll.duellant_1.punkte_spiel -=Decimal(0.5)
        duell_protokoll.duellant_2.punkte_spiel -=Decimal(0.5)
        duell_protokoll.save()
        duell_eingabe.duellant_nr = 2
        duell_eingabe.punkte = -Decimal(0.5)
        duell_eingabe.anmerkung = "neue Kandidaten mit Punktabzug"
    else:
        duell_eingabe.duellant_nr = 2
        duell_eingabe.anmerkung = "neue Kandidaten ohne Punktabzug"
    duell_eingabe.save()
    duellant_1, duellant_2 = sub_auslosen(gruppe.id)
    duell_protokoll = Duell_Protokoll.objects.create(
        protokoll = protokoll, gruppe = gruppe, duellant_1 = duellant_1, duellant_2 = duellant_2 
    ) 
    req.session['duell_id'] = duell_protokoll.id    
    if protokoll.wert:
        form = AufgabeFormZahl(req.POST)
    else:
        form = AufgabeFormStr(req.POST)
    if duell_protokoll.duellant_1.liga != duell_protokoll.duellant_2.liga:
        meldung = "Aufstiegsduell:"
    else:
        meldung = ""
    context = dict(protokoll = protokoll,  duell_protokoll = duell_protokoll, parameter = protokoll.parameter,   
    farbe_1 = farbe(duellant_1.punkte_spiel), farbe_2 = farbe(duellant_2.punkte_spiel), 
    form = form,    message_unten = protokoll.anmerkung, meldung = meldung)
    return render(req, 'aufgabe_duell.html', context)

def duell_loeschen(req):
    gruppe = Lerngruppe.objects.get(pk = req.session.get('gruppe_id'))
    gruppen = Lerngruppe.objects.filter(lehrer=req.user)
    if gruppe.lehrer != req.user:
        return HttpResponse("Zugriff verweigert")
    try:    
        duellanten = Duellant.objects.filter(profil__gruppe = gruppe)
    except:
        messages.error(req, "Diese Duellgruppe existiert nicht")        
        return render(req, 'lehrer/meine_gruppen.html', context={'gruppen': gruppen,})        
    if req.method == 'POST':
        nur_punkte = req.POST.get('nur_punkte', 'off') 
        bestaetigt = req.POST.get('bestaetigt', 'off')
        if bestaetigt == "on":
            zaehler = Zaehler.objects.filter(user = req.user.profil)
            for kategorie in zaehler:
                kategorie.aufgnr = 0
                kategorie.save()
            if nur_punkte == "on":
                for duellant in duellanten:
                    duellant.punkte = 0
                    duellant.spiele = 0
                    duellant.punkte_spiel = 0
                    duellant.pps = 0
                    duellant.platz = None
                    duellant.abwesend = False
                    duellant.aufsteiger = False
                    duellant.save()
                duell_eingabe = Duell_Eingabe.objects.filter(duell_protokoll__gruppe = gruppe)
                duell_eingabe.all().delete() 
            else:
                duellanten.all().delete()
        else:
            messages.error(req, "Löschen wurde abgebrochen!")
        return render(req, 'lehrer/meine_gruppen.html', context={'gruppen': gruppen,})
    return render(req, 'duell_loeschen.html' , context={'titel': "Duellgruppe löschen", 'gruppe' : gruppe}) 

def duell_how_to(req):
    return render(req, 'duell_how_to.html')    

def duell_protokoll(req, gruppe_id):
    gruppe = Lerngruppe.objects.get(pk = req.session.get('gruppe_id'))
    if gruppe.lehrer != req.user:
        return HttpResponse("Zugriff verweigert")
    else:
        duell_eingabe = Duell_Eingabe.objects.filter(duell_protokoll__gruppe=gruppe).order_by('id').reverse()
        form = DuellProtokollFilter#(
            #     req.POST, req.FILES, gruppe
            # )
        context = dict(duell_eingabe = duell_eingabe, gruppe = gruppe, form = form)
        return render(req, 'duell_protokoll.html', context)
