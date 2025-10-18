from datetime import datetime, date
from django.utils import timezone

from django.contrib.auth import logout
from django.contrib.auth.models import User
from django.shortcuts import render, redirect, get_object_or_404

from .models import Profil

from core.models import Protokoll, Zaehler

# Standardmäßig wird das echte Datum genommen.
# Für Tests kannst du TEST_DATE setzen.
TEST_DATE = None  
#TEST_DATE = date(2026, 1,10)

def get_today():
    """Gibt das aktuelle Datum zurück, oder ein Testdatum, wenn gesetzt."""
    return TEST_DATE or date.today()

def get_now():
    """Gibt die aktuelle Uhrzeit zurück, oder ein Testdatum mit Uhrzeit, wenn gesetzt."""
    if TEST_DATE:
        # Wenn TEST_DATE nur ein Datum ist, wandle es in datetime um
        return datetime.combine(TEST_DATE, datetime.min.time())
    return datetime.now()

def name_hj():
    heute = get_today()
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
    heute = get_today()
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

def check_hj(req):
    """Überprüft Halbjahr und Profil, gibt entweder Redirect, Render oder 'OK' zurück"""
    if not req.user.is_authenticated:
        return redirect('anmelden')

    email = req.user.email
    try:
        profil = req.user.profil
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

    heute = get_today()

    # Halbjahres-/Schuljahreswechsel prüfen
    if heute.month in (1, 7) and sub_note_anzeigen(profil):
        next_sj, next_hj = name_next_hj()
        if profil.hj == next_hj and profil.sj == next_sj:
            # User arbeitet schon im nächsten Halbjahr
            return redirect('uebersicht')

        sj, hj = name_hj()
        if profil.hj != hj or profil.sj != sj:#
            # User arbeitet noch im alten Halbjahr/Jahr
            return redirect('wiederanmeldung')

        #if heute.day > profil.voreinst["frage_hj"] and not profil.voreinst["no_hj"]:
        if not profil.keine_hj_frage:
            # Frage stellen, ob neues Halbjahr begonnen werden soll
            monat, wechsel = ("Juli", "Februar") if heute.month == 1 else ("Januar", "August")
            context = {'monat': monat, 'wechsel': wechsel}
            return render(req, 'naechstes_halbjahr.html', context)

        # Alles im Lot → keine Frage, kein Wechsel
        return "OK"

    # Kein Halbjahreswechsel aktuell → nur prüfen, ob Profil im richtigen Jahr/HJ ist
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
            sub_daten_loeschen(req)
            return "OK"
        
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
    profil = get_object_or_404(Profil, user=req.user)
    # Reset Voreinstellungen
    profil.keine_hj_frage =  False
    # Zähler zurücksetzen
    for zaehler in Zaehler.objects.filter(profil_id=profil.id):
        zaehler.fehler_zaehler = 0
        zaehler.lsg_zaehler = 0
        zaehler.hilfe_zaehler = 0
        zaehler.abbr_zaehler = 0
        zaehler.bonus = 0
        zaehler.save()
    halbjahr = None
    jahrgang = profil.jg
    klasse = profil.klasse
    if profil.hj == 2:
        # Halbjahreswechsel
        halbjahr = "Halbjahr"
        profil.halbjahr_ab = timezone.now()
        profil.save()
    else:
        # Schuljahreswechsel
        halbjahr = "Schuljahr"
        profil.schuljahr_ab = timezone.now()
        if profil.jg < 13:
            # Klasse hochzählen (nur Vorschlag!)
            if str(profil.jg) in profil.klasse:
                klasse = profil.klasse.replace(str(profil.jg), str(profil.jg + 1), 1)
            # Jahrgang + Stufe anpassen (nur intern, nicht im Template veränderbar)
            profil.jg += 1
            neue_stufe = stufe_aus_jg(profil.jg, profil.kurs)
            if neue_stufe > profil.stufe:
                profil.stufe = neue_stufe
        profil.klasse = klasse
        profil.save()
        jahrgang = profil.jg
    # Rückgabe für Template
    return {
        "halbjahr": halbjahr,
        "jahrgang": jahrgang,
        "klasse": klasse,
    }

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

