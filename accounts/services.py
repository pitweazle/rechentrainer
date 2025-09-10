from datetime import datetime
from django.utils import timezone

from django.contrib.auth import logout
from django.shortcuts import render, redirect, get_object_or_404

from .models import Profil
from django.contrib.auth.models import User

from core.models import Protokoll, Zaehler

def name_hj():
    heute = datetime.today()
    jahr = heute.year
    sj = jahr%100*100+jahr%100+1
    if heute.month in range(1,8):
        sj -= 101
    if heute.month in range(2,8):    
        hj = 2
    else:
        hj = 1
    return sj, hj           

def name_next_hj():
    heute = datetime.today()
    jahr = heute.year
    sj = jahr%100*100+jahr%100+1
    if heute.month == 1:
        hj = 2
        sj -=101
    else:
        hj = 1
    if heute.month > 7:
        hj = 2
    return sj, hj      

def sub_note_anzeigen(profil):
    if (profil.gruppe):
        note_anzeigen = True if profil.gruppe.note_anzeigen else False
    else:
        note_anzeigen = False
    return note_anzeigen

def stufe_aus_jg(jg, kurs="E"):
    stufe = 0
    if kurs == "i":
        stufe = 0
    else: 
        if jg < 5:
            stufe = 1
        else:
            if jg > 11:
                jg = 11
                kurs = "Y"
            stufe_liste = [2,4,12,20,26,32,50]
            if jg > 11:
                jg = 10
                kurs = "Y"
            stufe = stufe_liste[jg-5] 
            if kurs in ["Y","R","E","B"]:
                stufe +=1
    return stufe

def sub_daten_loeschen(req):
    profil = get_object_or_404(Profil, user = req.user)
    profil.voreinst["no_hj"] = False
    profil.voreinst["frage_hj"] = 0
    for zaehler in Zaehler.objects.filter(profil_id = profil.id): 
        zaehler.fehler_zaehler = 0  
        zaehler.lsg_zaehler = 0  
        zaehler.hilfe_zaehler = 0  
        zaehler.abbr_zaehler = 0 
        zaehler.bonus = 0 
        zaehler.save()
    if profil.hj == 2:
        halbjahr = "Halbjahr"
        profil.halbjahr_ab = timezone.now()
        profil.save()
    else:
        halbjahr = "Schuljahr"
        profil.schuljahr_ab = timezone.now()
        if profil.jg < 13:
            if str(profil.jg) in profil.klasse:
                profil.klasse = profil.klasse.replace(str(profil.jg), str(profil.jg+1),1)
            profil.jg +=1
            neue_stufe = stufe_aus_jg(profil.jg, profil.kurs)
            if neue_stufe > profil.stufe:
                profil.stufe = neue_stufe
        profil.save()
        return halbjahr

def quote_farbe(richtig, falsch, ungenuegend=1/3):
    try:
        quote = falsch / (richtig + falsch)
        if quote <= 0.1:
            return "gruen"
        elif quote <= ungenuegend:
            return "gelb"
        else:
            return "rot"
    except :
        return None

def check_hj(user, req):
    """Überprüft Halbjahr und Profil, gibt entweder Redirect oder 'OK' zurück"""
    if not user.is_authenticated:
        return redirect('anmelden')

    email = user.email
    try:
        profil = user.profil
    except Profil.DoesNotExist:
        # Fallback für doppelte Accounts
        zeilen = []
        doppelte_accounts = User.objects.filter(email=email, email__contains="@")
        for account in doppelte_accounts:
            try:
                profil = Profil.objects.get(profil=account)
                gesamt = Protokoll.objects.filter(profil=profil)
                zeilen.append((account, profil, gesamt.count()))
            except Profil.DoesNotExist:
                zeilen.append((account, None, ""))
        logout(req)
        return render(req, 'doppelte_accounts.html', {'zeilen': zeilen, 'email': email})

    heute = datetime.now()
    if heute.month in (1, 7) and sub_note_anzeigen(profil):
        next_sj, next_hj = name_next_hj()
        if profil.hj == next_hj and profil.sj == next_sj:
            return redirect('uebersicht')
        sj, hj = name_hj()
        if profil.hj != hj or profil.sj != sj:
            return redirect('wiederanmeldung')
        try:
            if heute.day > profil.voreinst.setdefault("frage_hj", 0) and not profil.voreinst.setdefault("no_hj", False):
                test = False  # nur Dummy, kann ggf. entfernt werden
        except:
            profil.voreinst["frage_hj"] = 0
            profil.voreinst["no_hj"] = False
            profil.save()
        if heute.day > profil.voreinst.get("frage_hj", 0) and not profil.voreinst.get("no_hj", False):
            monat, wechsel = ("Juli", "Februar") if heute.month == 1 else ("Januar", "August")
            context = {'monat': monat, 'wechsel': wechsel}
            return render(request, 'naechstes_halbjahr.html', context)
        return redirect('uebersicht')
    else:
        sj, hj = name_hj()
        if profil.hj == hj and profil.sj == sj:
            return "OK"
        else:
            if sub_note_anzeigen(profil):
                return redirect('neues_halbjahr')
            else:
                profil.hj = hj
                profil.sj = sj
                profil.save()
                sub_daten_loeschen(request)
    return redirect('uebersicht')
