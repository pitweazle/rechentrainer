import random
import json

from decimal import *

from django.contrib import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.http import HttpResponse 
from django.shortcuts import redirect, render,  get_object_or_404

from django.db.models import Count 

from core.forms import AufgabeFormZahl, AufgabeFormStr, AufgabeFormTab, AufgabeFormTerm
from .forms import Duellant_Aendern_Form

from accounts.models import Profil, Lerngruppe
from core.models import Kategorie, Protokoll, Zaehler 
from .models import  Duellant, Duell_Protokoll, Duell_Wertung

from core.views import aufgaben, kontrolle

# das Rechenduell
def duell_uebersicht(req, gruppe_id):
    gruppe = get_object_or_404(Lerngruppe, pk=gruppe_id)
    if gruppe.lehrer != req.user and not req.user.is_superuser:
        return HttpResponse("Zugriff verweigert")
    profil = get_object_or_404(Profil, user=req.user)
    profil.duell_gruppe = gruppe_id
    profil.save() 
    duellanten = Duellant.objects.filter(profil__gruppe=gruppe_id)
    for duellant in duellanten:
        duellant.punkte +=duellant.punkte_spiel
        duellant.punkte_spiel = 0
        if duellant.spiele != 0:
            duellant.pps = duellant.punkte/duellant.spiele
        duellant.save()
    zaehler = Zaehler.objects.filter(user=profil)
    for kategorie in zaehler:
        kategorie.aufgnr = 1
        kategorie.save()
    schueler_liste = Profil.objects.filter(gruppe=gruppe).order_by("user__profil__vorname")
    for schueler in schueler_liste:
        duellant, created = Duellant.objects.get_or_create(profil = schueler)
        if created:
            duellant.name = schueler.vorname
            duellant.save()
    dubletten = Duellant.objects.values('name').annotate(dubletten=Count('name')).filter(dubletten__gt=1)
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
    duellanten = Duellant.objects.filter(profil__gruppe = gruppe).order_by("liga", "platz", "profil")
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
    return render(req, 'duellant_aendern.html', {'gruppe_id': gruppe_id, 'duellanten': duellanten, 'duellant': duellant, 'form': form,})

def duell_aufgabe(req, slug):
    gruppe = Lerngruppe.objects.get(pk = req.session.get('gruppe_id'))
    if gruppe.lehrer != req.user:
        return HttpResponse("Zugriff verweigert")
    kategorie = get_object_or_404(Kategorie, slug = slug)
    user = req.user.profil
    duell_rang(gruppe.id)
    duellant_1, duellant_2 = sub_auslosen(gruppe.id)
    zaehler, created = Zaehler.objects.get_or_create(user = user, kategorie = kategorie)
    if zaehler.aufgnr == 0:     # Das ist jeweils die erste Aufgabe von 10
        zaehler.aufgnr = 1
    zaehler.aufgnr += 1
    zaehler.save()
    if zaehler.aufgnr > 10:
        return redirect('duell_uebersicht', gruppe.id)
    #hier wird die entsprechende Funktion aufgerufen und festgelegt, aus welchem Bereich (Typ) Aufgaben erzeugt werden
    #zunächst wird überprüft, ob für diese kategorie Einträge bei "Optionen" vorhanden sind:
    if not zaehler.optionen_text :  
        return redirect('optionen', slug)
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
    stufe = user.stufe
    #unter Umständen gibt es auch spezielle Aufgaben für A-Kurs und Gymnasium - dazu wird hier die Stufe um 0,2 hochgesetzt
    if kategorie.name in ("Prozentrechnung","Bruchteile"):
        if user.kurs == "A" or user.kurs == "Y":
            stufe = stufe + 0.2
    typ, typ2, titel, text, pro_text, frage, variable, einheit, anmerkung, lsg, hilfe_id, ergebnis, parameter = aufgaben(kategorie.zeile, jg = user.jg, stufe = stufe, aufgnr = zaehler.aufgnr, typ_anf = typ_anf, typ_end = zaehler.typ_end, optionen = "") 
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
        if "term" in protokoll.parameter["name"]:
            form = AufgabeFormTerm(req.POST)
        else:
            form = AufgabeFormTab(req.POST)
    else:
        if protokoll.wert:
            form = AufgabeFormZahl(req.POST)
        #wenn in den Aufgaben erg=None:
        else:
            form = AufgabeFormStr(req.POST)
    req.session['protokoll_id'] = protokoll.id  
    req.session['zaehler'] = zaehler.id    
    req.session['duell_id'] = duell_protokoll.id    
    context = dict(protokoll = protokoll,  duell_protokoll = duell_protokoll, parameter = parameter,   
        farbe_1 = "null", farbe_2 = "null", 
        form = form,    message_unten = anmerkung)
    return render(req, 'aufgabe_duell.html', context)

def sub_auslosen(gruppe_id):
    duellanten = Duellant.objects.filter(profil__gruppe=gruppe_id)
    duellanten_ids = []
    for duellant in duellanten:
        duellanten_ids.append(duellant.id)
    auswahl = (random.sample(duellanten_ids,2))
    duellant_1 = duellanten.get(id = auswahl[0])
    duellant_1.spiele +=1
    duellant_1.save()
    duellant_2 = duellanten.get(id = auswahl[1])
    duellant_2.spiele +=1
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

def duell_loesung(req):
    duell_protokoll = Duell_Protokoll.objects.get(pk = req.session.get('duell_id'))
    gruppe = get_object_or_404(Lerngruppe, pk=duell_protokoll.gruppe_id)
    protokoll = Protokoll.objects.get(pk = req.session.get('protokoll_id'))
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
        farbe_1 = farbe_1, farbe_2 = farbe_2, richtig = str(protokoll.eingabe).replace(".",","),
        message_unten = protokoll.anmerkung, hinweis = "Lösung")
    return render(req, 'aufgabe_duell.html', context)
 
def sub_punkte(duell_protokoll, duellant, eingabe, punkte):
    #duellant = Duellant.objects.get(name=duellant_name)
    duell_wertung = Duell_Wertung.objects.create(duell_protokoll = duell_protokoll, duellant = duellant)
    duellant.punkte_spiel += punkte
    duellant.save()
    duell_wertung.eingabe = eingabe
    duell_wertung.punkte = duellant.punkte_spiel
    duell_wertung.save()

def duell_kontrolle(req):
    gruppe = Lerngruppe.objects.get(pk = req.session.get('gruppe_id'))
    if gruppe.lehrer != req.user:
        return HttpResponse("Zugriff verweigert")
    protokoll = Protokoll.objects.get(pk = req.session.get('protokoll_id'))
    protokoll.versuche += 1
    duell_protokoll = Duell_Protokoll.objects.get(pk = req.session.get('duell_id'))
    #wenn in den Aufgaben in "erg" eine Zahl steht
    if "tab" in protokoll.parameter["name"]:
        if "term" in protokoll.parameter["name"]:
            form = AufgabeFormTerm(req.POST)
        else:
            form = AufgabeFormTab(req.POST)
    else:
        if protokoll.wert:
            form = AufgabeFormZahl(req.POST)
        #wenn in den Aufgaben erg=None:
        else:
            form = AufgabeFormStr(req.POST)
    #Aufgabe beantwortetA
    if form.is_valid():
        # zunächst Einträge im Protokoll:
        if "tab" in protokoll.parameter["name"]:                            # für Wertetabellen
            eingabe = []
            if "term" in protokoll.parameter["name"]:                            # für Terme
                eingabe.append(form.cleaned_data['y0'])
                eingabe.append(form.cleaned_data['y1'])
            eingabe.append(form.cleaned_data['y2'])
            eingabe.append(form.cleaned_data['y3'])
            eingabe.append(form.cleaned_data['y4'])
            pro_eingabe = "; ".join([str(e) for e in eingabe]).replace(".",",")
        else:
            eingabe = pro_eingabe = form.cleaned_data['eingabe']
            protokoll.eingabe = pro_eingabe
        #bei der Erstellung der Aufgabe wird der Abbrechen_zähler um Eins hochgezählt, wenn eine Eingabe erfolgt wird das hier wieder rückgängig gemacht.
        #Dadurch wird der Zähler hochgesetzt, wenn mit F5 eine neue Aufgabe erzeugt wird.
        protokoll.abbr = False
        protokoll.end = timezone.now()
        protokoll.save()
        #hier wird die Eingabe überprüft:
        wertung, rueckmeldung = kontrolle(eingabe, protokoll.wert, protokoll.loesung, protokoll.id)
        if wertung <= 2:
            tabelle = 0
            richtig = wertung
        else:
            if wertung >= 3000:                                   # Anzahl der Einträge in der Tabelle
                tabelle = 3
                richtig = str(wertung).count("1")
                falsch = str(wertung).count("0")
            if wertung >= 300000:
                tabelle = 5
        duellant_name = req.POST.get('duellant')
        beide = True if duellant_name == "gleich schnell" else False
        #wenn Eingabe richtig:
        if (wertung > 0 and tabelle == 0) or (richtig == tabelle and tabelle > 0) :
            if tabelle > 0:                  # alle Eingaben in der Tabelle richtig
                rueckmeldung = "Alle Werte waren richtig richtig!"
                zaehler.aufgnr += tabelle
                # entfernt eventuelle Einträge "r"
                protokoll.wertung = protokoll.wertung.replace("r", "") + richtig*"r"
            elif tabelle == 0 :
                if "enauer" in rueckmeldung:
                    rueckmeldung = "Die letzte Aufgabe war fast richtig!"+ rueckmeldung
                else:
                    rueckmeldung = "Die letzte Aufgabe war richtig!"+ rueckmeldung
            punkte = 1
            if beide:
                duellant = duell_protokoll.duellant_1
                sub_punkte(duell_protokoll, duellant, eingabe, punkte )
                duellant = duell_protokoll.duellant_2
                sub_punkte(duell_protokoll, duellant, eingabe, punkte )
            else: 
                duellant = Duellant.objects.get(name=duellant_name)
                sub_punkte(duell_protokoll, duellant, eingabe, punkte )
            messages.info(req, f'{rueckmeldung}')
            farbe_1 = farbe(duell_protokoll.duellant_1.punkte_spiel)
            farbe_2 = farbe(duell_protokoll.duellant_2.punkte_spiel)
            context = dict(protokoll = protokoll, duell_protokoll = duell_protokoll, parameter = protokoll.parameter,   
                farbe_1 = farbe_1, farbe_2 = farbe_2, richtig = str(protokoll.eingabe).replace(".",","),
                message_unten = protokoll.anmerkung)
            return render(req, 'aufgabe_duell.html', context)
        #wenn Aufgabe falsch:
        else: 
            if wertung < 0:                             #wenn mithilfe des Eintrags "indiv_1" ein Teilpunkt vergeben wurde, wird dies hier angezeigt:
                messages.info(req, rueckmeldung)  
                wertung = -1 
            if wertung == -1:
                punkte = Decimal(-0.5)
                messages.info(req, f'Die letzte Aufgabe war leider falsch! Versuche: {protokoll.versuche}')#, {msg}') 
            else:
                if not "tab" in protokoll.parameter["name"]:
                    messages.info(req, f'{rueckmeldung}')   #gibt eine Rückmeldung wenn "indiv" bei Lösung steht 
            if beide:
                duellant = duell_protokoll.duellant_1
                sub_punkte(duell_protokoll, duellant, eingabe, punkte )
                duellant = duell_protokoll.duellant_2
                sub_punkte(duell_protokoll, duellant, eingabe, punkte )
            else: 
                duellant = Duellant.objects.get(name=duellant_name)
                sub_punkte(duell_protokoll, duellant, eingabe, punkte )
    farbe_1 = farbe(duell_protokoll.duellant_1.punkte_spiel)
    farbe_2 = farbe(duell_protokoll.duellant_2.punkte_spiel)
    context = dict(protokoll = protokoll, duell_protokoll = duell_protokoll, parameter = protokoll.parameter,   
        farbe_1 = farbe_1, farbe_2 = farbe_2, 
        form = form,    message_unten = protokoll.anmerkung)
    return render(req, 'aufgabe_duell.html', context)

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
    #duell_wertung = Duell_Wertung.objects.create(duell_protokoll = duell_protokoll, duellant = duellant) 
    if punkte == "plus":
        duellant.punkte_spiel +=Decimal(0.5)
        #duell_wertung.punkte +=Decimal(0.5)
    elif punkte == "minus":
        duellant.punkte_spiel -=Decimal(0.5)
        #duell_wertung.punkte -=Decimal(0.5)
    duellant.save()
    #duell_wertung.save()
    farbe_1 = farbe(duell_protokoll.duellant_1.punkte_spiel)
    farbe_2 = farbe(duell_protokoll.duellant_2.punkte_spiel)
    if protokoll.wert:
        form = AufgabeFormZahl(req.POST)
    else:
        form = AufgabeFormStr(req.POST)
    context = dict(protokoll = protokoll, duell_protokoll = duell_protokoll, parameter = protokoll.parameter,   
        farbe_1 = farbe_1, farbe_2 = farbe_2, 
        form = form,    message_unten = protokoll.anmerkung)
    return render(req, 'aufgabe_duell.html', context)

def neu_auslosen(req, mit):
    gruppe = Lerngruppe.objects.get(pk = req.session.get('gruppe_id'))
    if gruppe.lehrer != req.user:
        return HttpResponse("Zugriff verweigert")
    protokoll = Protokoll.objects.get(pk = req.session.get('protokoll_id'))
    duell_protokoll = Duell_Protokoll.objects.get(pk = req.session.get('duell_id'))
    print("alt: ",duell_protokoll.id)
    if mit == "mit":
        duell_protokoll.duellant_1.punkte_spiel -=Decimal(0.5)
        duell_protokoll.duellant_2.punkte_spiel -=Decimal(0.5)
        duell_protokoll.save()
    duellant_1, duellant_2 = sub_auslosen(gruppe.id)
    duell_protokoll_neu = Duell_Protokoll.objects.create(
        protokoll = protokoll, gruppe = gruppe, duellant_1 = duellant_1, duellant_2 = duellant_2 
    ) 
    print("neu: ",duell_protokoll_neu.id)
    req.session.pop('duell_id', duell_protokoll_neu.id)
    #req.session.modified = True 
    if protokoll.wert:
        form = AufgabeFormZahl(req.POST)
    else:
        form = AufgabeFormStr(req.POST)
    context = dict(protokoll = protokoll,  duell_protokoll = duell_protokoll, parameter = protokoll.parameter,   
    farbe_1 = farbe(duellant_1.punkte_spiel), farbe_2 = farbe(duellant_2.punkte_spiel), 
    form = form,    message_unten = protokoll.anmerkung)
    return render(req, 'aufgabe_duell.html', context)

