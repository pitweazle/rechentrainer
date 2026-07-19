from datetime import date, datetime, timedelta, time

from decimal import Decimal

import string
import random

import json
from pathlib import Path

from django.utils import timezone

from django.shortcuts import render, redirect, get_object_or_404

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group
from django.contrib import messages

from django.http import HttpResponse, HttpResponseBadRequest, FileResponse, Http404
from django.conf import settings

from django.views.decorators.csrf import csrf_exempt

from django.db.models import Max, Sum, Count, F, Q
from django.db.models import Sum, Case, When, IntegerField
from django.db import connection

from .forms import Register_Form, Profil_Form, Login_Form, Suchen_Form, Loeschen_Form, Zusammen_Form, Abmelden_Form
from .forms import Profil_Aendern_Form, Ort_Form, Lehrer_Aendern_Form, Gruppe_Neu_Form, Gruppe_Aendern_Form, Schueler_Aendern_Form 
from .forms import ProtokollFilter_neu, Start_Datum, End_Datum

from .models import Profil, Schule, Lerngruppe, ExterneSchnittstelleConfig, Geloescht, wahl_kurs
from .services import check_hj, stufe_aus_jg, sub_daten_loeschen, name_hj, name_next_hj, quote_farbe

from core.models import Zaehler, Profil, Kategorie, Protokoll

from mathetests.models import Test

# Dies ist die Startseite:
def index(req):
    if 'duell' in req.session:
        del req.session['duell']
    anz_angemeldet = Profil.objects.count()
    anz_lehrer = User.objects.filter(groups__name="Lehrer").count()
    anz_aktuell = Protokoll.objects.count()
    # gelöschte Aufgaben aus JSON
    counter_file = Path(settings.BASE_DIR) / "core" / "zaehler_geloeschte_aufgaben.json"
    try:
        data = json.loads(counter_file.read_text())
        anz_geloescht = data.get("anzahl", 0)
    except FileNotFoundError:
        anz_geloescht = 0
    anz_gesamt = anz_aktuell + anz_geloescht
    lehrer = User.objects.filter(pk=req.user.id, groups__name='Lehrer').exists()
    tests = []
    if req.user.is_authenticated:
        profil = Profil.objects.select_related("gruppe").filter(user=req.user).first()
        if profil and profil.gruppe_id:
            tests = Test.objects.filter(gruppe = profil.gruppe).order_by("-created_at")
    else:
        profil = None
    return render(req, "index.html", {"profil": profil, "lehrer": lehrer, "anz_angemeldet": anz_angemeldet, "anz_lehrer": anz_lehrer, "anz_aufg": anz_gesamt, "tests": tests, })

def datenschutz(req):
    return render(req, 'datenschutz.html', context={'titel': "Datenschutz",})

def stimmen(req):
    return render(req, 'stimmen.html', context={'titel': "Stimmen zum Rechentrainer",})

def stufen(req):
    return render(req, 'lehrer/stufen.html', context={'titel': "Was bedeuten die Stufen?",})

# registrieren und anmelden:
def registrieren(req):
    reg_form = Register_Form()
    profil_form = Profil_Form()  
    datenschutz = ""
    if req.method == 'POST':
        neues_halbjahr = req.POST.get('neu', 'nein')
        datenschutz = req.POST.get('datenschutz', 'off')
        reg_form = Register_Form(req.POST)
        profil_form = Profil_Form(req.POST) 
        if datenschutz == "on":
            if  reg_form.is_valid() and profil_form.is_valid(): 
                user = reg_form.save()
                profil = profil_form.save(commit=False)
                kurs = profil_form.cleaned_data['kurs']
                jg = profil_form.cleaned_data['jg']
                profil.stufe = stufe_aus_jg(jg, kurs)
                sj, hj = name_hj()
                profil.sj = sj
                profil.hj = hj
                profil.user = user
                username = reg_form.cleaned_data['username']
                password = reg_form.cleaned_data['password1']
                user = authenticate(username=username, password=password)
                login(req, user)
                group = Group.objects.get(name='Schüler')
                user.groups.add(group)
                if neues_halbjahr.lower() == 'ja':
                    sj, hj = name_next_hj()            
                    profil.sj = sj
                    profil.hj = hj
                if req.POST.get('cookie_loeschen') == 'on':
                    req.session.set_expiry(0)
                if profil.hj == 1:
                    profil.schuljahr_ab = timezone.now()
                else:
                    profil.halbjahr_ab = timezone.now()
                profil.save()
                return redirect(ort_wahl)
    context = {'reg_form' : reg_form, 'profil_form' : profil_form, 'datenschutz': datenschutz,'titel': "Registrieren"} 
    return render(req, 'registrieren.html', context)

def anmelden(req):
    titel = "Anmelden" 
    if req.method == 'POST':
        #get_expire_at_browser_close()
        form = Login_Form(req.POST)
        if  form.is_valid ():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']            
            user = authenticate(req, username=username, password=password)
            cookie_loeschen = req.POST.get('cookie_loeschen') 
            if cookie_loeschen == 'on':
                req.session.set_expiry(0)
            # if user is not None:
            #     login(req, user)
            #     return hj_pruefen(req)
            if user is not None:
                login(req, user)
                # Halbjahr-Check wie in core/main
                result = check_hj(req)
                if isinstance(result, HttpResponse):
                    return result
                return redirect('uebersicht')

        titel = "Username und/oder Passwort stimmen nicht"
    form = Login_Form()
    context = {'form' : form, 'titel': titel} 
    return render(req, 'anmelden.html', context)

# Hilfsfunktion, um ein zufälliges Passwort für den neuen Django-User zu generieren
def generiere_zufaelliges_passwort():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=24))

@csrf_exempt
def lti_launch(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("Nur POST-Anfragen erlaubt.")
    consumer_key = request.POST.get('oauth_consumer_key')
    try:
        config = ExterneSchnittstelleConfig.objects.get(consumer_key=consumer_key, typ='moodle')
    except ExterneSchnittstelleConfig.DoesNotExist:
        return HttpResponseBadRequest("Unbekannter oder ungültiger Consumer Key.")

    # Moodle-Daten auslesen
    moodle_uid = request.POST.get('user_id') 
    vorname = request.POST.get('lis_person_name_given', '').strip()
    nachname = request.POST.get('lis_person_name_family', '').strip()
    moodle_email = request.POST.get('lis_person_contact_email_primary', '').strip()
    moodle_rollen = request.POST.get('roles', 'Learner')
    
    if 'Instructor' in moodle_rollen or 'Teacher' in moodle_rollen:
        ziel_gruppen_name = "Lehrer"
    else:
        ziel_gruppen_name = "Schüler"

    # 1. WENN DATEN VON MOODLE FEHLERHAFT -> Fehlermeldung "falsche Daten"
    if not moodle_uid or not vorname or not nachname:
        return HttpResponseBadRequest("Falsche oder unvollständige Moodle-Daten übermittelt.")
        
    # 2. WENN ID SCHON IM PROFIL -> Einloggen
    try:
        profil = Profil.objects.get(moodle_uid=moodle_uid)
        user = profil.user
        
        # Gruppe und E-Mail pflegen
        gruppe_obj = Group.objects.filter(name=ziel_gruppen_name).first()
        if gruppe_obj:
            user.groups.add(gruppe_obj)
        if moodle_email and user.email != moodle_email:
            user.email = moodle_email
            user.save()
            
        login(request, user)
        return redirect('index')
    except Profil.DoesNotExist:
        pass

    # Schule für die Namensprüfung holen
    schule_objekt = Schule.objects.filter(dienststellen_nr=consumer_key).first()
    if not schule_objekt:
        return HttpResponseBadRequest(f"Keine Schule mit ID '{consumer_key}' gefunden.")

    # 3. WENN KEINE ID, ABER NAME STIMMT ÜBEREIN -> ID eintragen und einloggen
    profil = Profil.objects.filter(vorname=vorname, nachname=nachname, schule=schule_objekt).first()
    if profil:
        user = profil.user
        profil.moodle_uid = moodle_uid
        profil.save()
        
        gruppe_obj = Group.objects.filter(name=ziel_gruppen_name).first()
        if gruppe_obj:
            user.groups.add(gruppe_obj)
        if moodle_email and user.email != moodle_email:
            user.email = moodle_email
            user.save()
            
        login(request, user)
        return redirect('index')

    # 4. WENN KEINE ID UND KEINE NAMENSÜBEREINSTIMMUNG -> Daten merken und ab zur Frage!
    request.session['moodle_launch_data'] = {
        'moodle_uid': moodle_uid,
        'vorname': vorname,
        'nachname': nachname,
        'email': moodle_email,
        'schule_id': schule_objekt.id,
        'gruppe': ziel_gruppen_name,
        'jg': request.POST.get('custom_jg', request.POST.get('jg', 5)),
        'klasse': request.POST.get('context_title', 'Moodle-Kurs')[:10]
    }
    
    return redirect('moodle_entscheidung')

@csrf_exempt
def moodle_entscheidung(request):
    moodle_data = request.session.get('moodle_launch_data')
    if not moodle_data:
        return redirect('index')
    if request.method == 'POST':
        aktion = request.POST.get('aktion')
        # A) Registrierungs-Formular anzeigen
        if aktion == 'neu_registrieren':
            context = {
                'moodle_vorname': moodle_data.get('vorname', ''),
                'moodle_nachname': moodle_data.get('nachname', ''),
                'moodle_email': moodle_data.get('email', ''),
                'kurs_choices': wahl_kurs.choices,
            }
            request.session['moodle_launch_data'] = moodle_data
            return render(request, 'SSO/moodle_registrierung.html', context)
        # B) Registrierung speichern und User/Profil anlegen
        elif aktion == 'registrierung_speichern':
            reg_vorname = request.POST.get('reg_vorname', '').strip()
            reg_nachname = request.POST.get('reg_nachname', '').strip()
            reg_email = request.POST.get('reg_email', '').strip()
            reg_klasse = request.POST.get('reg_klasse', '')[:10]
            reg_jg = request.POST.get('reg_jg', '').strip()
            reg_kurs = request.POST.get('reg_kurs', '').strip()

            username = f"moodle_{moodle_data['moodle_uid'][:20]}"
            zufalls_passwort = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))

            # User erstellen
            user = User.objects.create_user(username=username, email=reg_email, password=zufalls_passwort)

            # Gruppe zuweisen
            gruppe_obj = Group.objects.filter(name=moodle_data['gruppe']).first()
            if gruppe_obj:
                user.groups.add(gruppe_obj)

            # Profil erstellen
            schule_obj = Schule.objects.get(id=moodle_data['schule_id'])
            Profil.objects.create(
                user=user,
                moodle_uid=moodle_data['moodle_uid'],
                vorname=reg_vorname,
                nachname=reg_nachname,
                schule=schule_obj,
                jg=reg_jg,
                klasse=reg_klasse,
                kurs=reg_kurs
            )

            login(request, user)
            if 'moodle_launch_data' in request.session:
                del request.session['moodle_launch_data']

            # Erfolgsmeldung
            context = {
                'username': username,
                'email': reg_email,
            }
            return render(request, 'SSO/moodle_erfolg.html', context)
        # C) Bestehenden User verknüpfen
        elif aktion == 'verknuepfen':
            user_input = request.POST.get('username_eingabe')
            pass_input = request.POST.get('passwort_eingabe')
            alter_user = authenticate(request, username=user_input, password=pass_input)

            if alter_user is not None:
                alter_profil = alter_user.profil
                alter_profil.moodle_uid = moodle_data['moodle_uid']
                alter_profil.save()

                # E-Mail von Moodle übernehmen, falls User bisher keine hatte
                if moodle_data.get('email') and not alter_user.email:
                    alter_user.email = moodle_data['email']
                    alter_user.save()

                login(request, alter_user)
                if 'moodle_launch_data' in request.session:
                    del request.session['moodle_launch_data']
                return redirect('index')
            else:
                return render(request, 'SSO/sso_weiche.html', {
                    'vorname': moodle_data['vorname'],
                    'nachname': moodle_data['nachname'],
                    'error_message': 'Ungültiger Benutzername oder Passwort.'
                })
        # D) Abbrechen
        elif aktion == 'abbrechen':
            if 'moodle_launch_data' in request.session:
                del request.session['moodle_launch_data']
            return redirect('index')
    # GET-Request: Hauptauswahl anzeigen
    return render(request, 'SSO/sso_weiche.html', {
        'vorname': moodle_data['vorname'],
        'nachname': moodle_data['nachname']
    })

@csrf_exempt
def simulation_view(request):
    if request.method == 'POST':
        # Erstelle eine Fake-POST-Anfrage für lti_launch
        from django.http import HttpRequest
        from accounts.views import lti_launch

        # Fake-Request erstellen
        fake_request = HttpRequest()
        fake_request.method = 'POST'
        fake_request.POST = {
            'oauth_consumer_key': request.POST.get('schule_id', 'DE-HE-6072'),  # Consumer Key = Dienststellennr
            'user_id': request.POST.get('uid', 'test_franz'),  # Moodle-UID
            'lis_person_name_given': request.POST.get('vorname', 'Franz'),
            'lis_person_name_family': request.POST.get('nachname', 'Musterschüler'),
            'lis_person_contact_email_primary': request.POST.get('email', 'test@example.de'),
            'roles': request.POST.get('gruppe', 'Learner'),  # Moodle-Rollen: "Learner" oder "Instructor"
            'context_title': request.POST.get('klasse', 'Testklasse'),
            'custom_jg': request.POST.get('jg', 6),
        }
        fake_request.session = request.session

        # Rufe lti_launch auf und gib die Antwort zurück
        return lti_launch(fake_request)

    # HTML-Formular für die Simulation (direkt in der View)
    return HttpResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Moodle-LTI-Simulation (realistisch)</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
                form { background: #f5f5f5; padding: 20px; border-radius: 8px; }
                input, select, button { padding: 8px; margin: 5px 0; width: 100%; box-sizing: border-box; }
                button { background: #28a745; color: white; border: none; cursor: pointer; }
            </style>
        </head>
        <body>
            <h1>Moodle-LTI-Simulation (für lti_launch)</h1>
            <p>Simuliert eine echte Moodle-LTI-Anfrage an <code>lti_launch</code>.</p>
            <form method="POST">
                <label>Consumer Key (Dienststellennr):</label>
                <input type="text" name="schule_id" value="DE-HE-6072"><br>

                <label>Moodle UID:</label>
                <input type="text" name="uid" value="test_franz"><br>

                <label>Vorname:</label>
                <input type="text" name="vorname" value="Franz"><br>

                <label>Nachname:</label>
                <input type="text" name="nachname" value="Musterschüler"><br>

                <label>E-Mail:</label>
                <input type="email" name="email" value="test@example.de"><br>

                <label>Gruppe (Moodle-Rolle):</label>
                <select name="gruppe">
                    <option value="Learner">Schüler (Learner)</option>
                    <option value="Instructor">Lehrer (Instructor)</option>
                </select><br>

                <label>Jahrgang:</label>
                <input type="number" name="jg" value="6"><br>

                <label>Klasse:</label>
                <input type="text" name="klasse" value="Testklasse"><br>

                <button type="submit">LTI-Anfrage an lti_launch senden</button>
            </form>
        </body>
        </html>
    """)

def account_loeschen(req):
    try:    
        user = User.objects.get(pk = req.user.id)
    except:
        messages.error(req, "Es ist kein Benutzer angemeldet!!")        
        return render(req, 'index.html')        
    if req.method == 'POST':
        bestaetigt = req.POST.get('bestaetigt', 'off')        
        if bestaetigt == "on":
            logout(req)
            user.delete()
            messages.success(req, "Dein Account und alle deine Daten wurden gelöscht!")
        else:
            messages.error(req, "Löschen wurde abgebrochen!")
        return render(req, 'index.html')
    return render(req, 'admin/account_loeschen.html', context={'titel': "Account löschen",}) 

def naechstes_halbjahr(req):
    if req.method == 'POST':
        neues_halbjahr = req.POST.get('neu', 'nein')
        keinefragen = req.POST.get('keinefrage') 
        profil = get_object_or_404(Profil, user = req.user)
        if neues_halbjahr.lower() == 'ja':
            # Nächste Werte bestimmen
            sj, hj = name_next_hj()          # gibt "kommendes" Schuljahr + Halbjahr zurück
            war_hj = getattr(profil, "hj", None)  # bisheriges Halbjahr (falls gebraucht)

            # Ist es ein NEUES SCHULJAHR? (typisch: vorher 2 -> jetzt 1)
            ist_neues_schuljahr = (hj == 1)

            # Jahrgang nur bei neuem Schuljahr erhöhen
            if ist_neues_schuljahr:
                profil.jg = (profil.jg or 0) + 1

            # Profil aktualisieren
            profil.hj = hj
            profil.sj = sj
            if ist_neues_schuljahr:
                profil.schuljahr_ab = timezone.now()
            else:
                profil.halbjahr_ab = timezone.now()
            profil.save()  # wichtig!

            # Anzeige-Label festlegen (nicht dem Helper überlassen)
            label = "Schuljahr" if ist_neues_schuljahr else "Halbjahr"

            # Optional: vorhandene Daten aufräumen, aber Ausgabefelder gezielt setzen
            info = sub_daten_loeschen(req) or {}
            info.update({
                "halbjahr": label,            # steuert "Ein neues {{ halbjahr }} hat begonnen"
                "jahrgang": profil.jg,  # für evtl. Anzeige
                "klasse": info.get("klasse"), # wenn du das hast/anzeigen willst
            })

            return render(req, "neues_halbjahr.html", context=info)
        if keinefragen == "on":
            profil.keine_hj_frage = True
        profil.save()  
        heute = datetime.now()
        if heute.month == 1 or heute.month == 7: 
            if heute.day > 25:         
                if profil.hj == 2:
                    monat = "August"
                else:
                    monat = "Februar" 
                return render(req, 'zweite_frage.html', context={'monat': monat})          
    return redirect('index')

def doch_neues_halbjahr(req):
    profil = get_object_or_404(Profil, user=req.user)
    sj, hj = name_next_hj()
    profil.hj = hj
    profil.sj = sj
    profil.save()
    context = sub_daten_loeschen(req)
    return render(req, 'neues_halbjahr.html', context)

def neues_halbjahr(req):
    profil = get_object_or_404(Profil, user = req.user)
    sj, hj = name_hj()
    profil.hj = hj
    profil.sj = sj
    profil.save()
    context = sub_daten_loeschen(req)
    return render(req, 'neues_halbjahr.html', context)

def wiederanmeldung(req):
    profil = get_object_or_404(Profil, user=req.user)
    sj, hj = name_hj()
    profil.hj = hj
    profil.sj = sj
    profil.save()
    context = sub_daten_loeschen(req)
    return render(req, 'neues_schuljahr.html', context)

# für Schüler
def profil(req):
    if User.objects.filter(pk=req.user.id, groups__name='Lehrer').exists():
        return redirect('profil_lehrer')
    try:
        schueler = get_object_or_404(Profil, user=req.user)
    except:
        return HttpResponse("Zugriff verweigert")        
    profil_form = Profil_Aendern_Form(instance=schueler,)
    if req.method == 'POST':
        details = req.POST.get('details') 
        if details:
            schueler.details = True
        else:
            schueler.details = False
        schueler.save()   
        profil_form = Profil_Aendern_Form(req.POST, instance=schueler)
        if  profil_form.is_valid():
            profil_form.save()
            return redirect('index')
        ort = Ort_Form(req.POST)
        if  ort.is_valid():
            ort_wahl = ort.cleaned_data['ort'] 
            if ort_wahl == None:
                schueler.schule = None
                schueler.gruppe = None
                schueler.save() 
                return render(req, 'schueler/keine_gruppe.html', context={'titel': "en Schulort"})
            schueler.ort=ort_wahl
            schueler.save()
            schulen = Schule.objects.filter(ort_id = ort_wahl)
            return render(req, 'schule_wahl.html', context={'schulen':schulen, 'ort':ort_wahl, 'titel': "Schule wählen"})
    else:
        ort_form = Ort_Form()
        ort_wahl = ""
    context = {'schueler': schueler, 'profil_form': profil_form, 'ort': ort_form, 'titel': "Profil", }
    return render(req, 'schueler/profil.html', context)

#Statistik
def bestenliste(req):
    from core.views import soll_berechnung
    sj, hj = name_hj()
    alleschueler = []
    schueler = Profil.objects.all()
    for s in schueler:
        profil_gruppe = s.gruppe
        if profil_gruppe:
            startdatum = s.gruppe.erstellt_am
        else:
            startdatum = s.user.date_joined
        schulwoche, woche_halbjahr, soll_hj, soll_kat, pflicht_kat = soll_berechnung(sj, hj, s.jg, s.jg*10, startdatum) 
        protokoll = Protokoll.objects.filter(profil = s)
        summe = protokoll.aggregate(sum=Sum('richtig'))['sum']
        summe = int(summe) if isinstance(summe, Decimal) else (summe or 0)

        protokoll = protokoll.filter(sj = sj)
        # sjsumme = protokoll.aggregate(sum=Sum('richtig'))['sum']
        # sjsumme = int(summe) if isinstance(sjsumme, Decimal) else (sjsumme or 0)

        protokoll = protokoll.filter(hj = hj)
        hjsumme = protokoll.aggregate(sum=Sum('richtig'))['sum']
        hjsumme = int(summe) if isinstance(hjsumme, Decimal) else (hjsumme or 0)


        schuelerliste = {"profil": s, "hjsumme": hjsumme, "summe": summe, "soll": soll_hj}
        alleschueler.append(schuelerliste)
    hjschueler = sorted(
        [entry for entry in alleschueler if entry["hjsumme"] > entry["soll"]], 
        key=lambda x: x["hjsumme"], 
        reverse=True
        )[:10] 
    # sjschueler = sorted(
    #     [entry for entry in alleschueler if entry["sjsumme"] > 0], 
    #     key=lambda x: x["sjsumme"], 
    #     reverse=True
    #     )[:10]
    gesamtschueler = sorted(
        [entry for entry in alleschueler if entry["summe"] > 0], 
        key=lambda x: x["summe"], 
        reverse=True
        )[:10]

    gruppe = Lerngruppe.objects.all()
    hjgruppen = []
    bestgruppen = []
    for g in gruppe:
        schulwoche, woche_halbjahr, soll_hj, soll_kat, pflicht_kat = soll_berechnung(sj, hj, g.jg, g.jg*10, g.erstellt_am) 
        mitglieder = Profil.objects.filter(gruppe = g).count()
        if mitglieder > 0:
            protokoll = Protokoll.objects.filter(profil__gruppe=g)
            summe = protokoll.aggregate(sum=Sum('richtig'))['sum']
            summe = int(summe) if isinstance(summe, Decimal) else (summe or 0)
            #if summe>0:
                #print(g, soll_hj, int(summe/mitglieder))
            protokoll = protokoll.filter(sj = sj)
            # sjsumme = protokoll.aggregate(sum=Sum('richtig'))['sum']
            # sjsumme = int(sjsumme) if isinstance(sjsumme, Decimal) else (sjsumme or 0)

            protokoll = protokoll.filter(hj = hj)
            hjsumme = protokoll.aggregate(sum=Sum('richtig'))['sum']
            hjsumme = int(hjsumme) if isinstance(hjsumme, Decimal) else (hjsumme or 0)

            if hjsumme > mitglieder*soll_hj*0.5:
                gruppenliste = {"gruppe": g, "mitglieder": mitglieder, 
                                "hjsumme": hjsumme, "hjschnitt": round(hjsumme/mitglieder), 
                                "summe": summe, "summeschnitt": round(summe/mitglieder)}
                hjgruppen.append(gruppenliste)

            if summe/mitglieder > soll_hj:
                gruppenliste = {"gruppe": g, "mitglieder": mitglieder, 
                                "hjsumme": hjsumme, "hjschnitt": round(hjsumme/mitglieder), 
                                "summe": summe, "summeschnitt": round(summe/mitglieder)}
                bestgruppen.append(gruppenliste)

        
        hjgruppen = sorted(
            [entry for entry in hjgruppen], 
            key=lambda x: x["hjsumme"], 
            reverse=True
            )[:10]
        
        bestgruppen = sorted(
            [entry for entry in bestgruppen], 
            key=lambda x: x["summe"], 
            reverse=True
            )[:10]

    context= {'hjliste': hjschueler, 'gesamtliste': gesamtschueler, 'hjgruppen': hjgruppen, 'bestgruppen': bestgruppen}
    return render(req, 'bestenliste.html', context)

def statistik(req):
    kategorien = Kategorie.objects.all().order_by('zeile')
    protokoll = Protokoll.objects.all()
    gesamt = protokoll.count()
    kategorienliste = []
    max = 0
    for kategorie in kategorien:
        protokoll = Protokoll.objects.filter(kategorie = kategorie)
        anzahl = [kategorie, protokoll.count(), ]
        kategorienliste.append(anzahl)
        if protokoll.count() > max:
            max = protokoll.count()
    for kategorie in kategorienliste:
        kategorie.append("width:"+str(kategorie[1]/max*100)+"%")
    return render(req, 'statistik.html', context= {'gesamt': gesamt, 'kategorien': kategorienliste})
  
# wird nur bei der Registrierung aufgerufen
def ort_wahl(req):
    ort_form = Ort_Form()
    if req.method == 'POST':
        ort_form = Ort_Form(req.POST) 
        if  ort_form.is_valid():
            ort_wahl = ort_form.cleaned_data['ort']
            if ort_wahl == None:
                return render(req, 'schueler/keine_gruppe.html', {'titel': "en Schulort"})
            else:
                profil = get_object_or_404(Profil, user = req.user)
                schulen = Schule.objects.filter(ort_id = ort_wahl)
                return render(req, 'schule_wahl.html', context={ 'schulen': schulen, 'titel': "Schule wählen"})
    return render(req, 'ort_wahl.html', context={'ort_form': ort_form, 'titel': "Schulort wählen"})

def schule_wahl(req, schule_id):
    try:
        profil = get_object_or_404(Profil, user = req.user)
    except:
        return redirect('anmelden')
    try:
        schule = get_object_or_404(Schule, id=schule_id)
    except:
        profil.schule = None
        profil.save()
        return render(req, 'schueler/keine_gruppe.html', {'titel': "en Schulort"})
    lehrer_liste =User.objects.filter(Q(groups__name="Lehrer"), Q(profil__schule = schule_id) | Q(profil__zweite_schule = schule_id))
    profil.schule = schule
    profil.save()
    if profil.klasse.lower() == "lehrer":
        return render(req, 'lehrer/wahl_fertig.html', {'titel': "fertig"})
    else:
        return render(req, 'schueler/lehrer_wahl.html', context={'lehrer_liste': lehrer_liste, 'schule': schule_wahl, 'titel': "Lehrer/in wählen"}) 

def lehrer_wahl(req, lehrer_id):
    try:
        lehrer = get_object_or_404(Profil, user_id = lehrer_id)
        gruppen = Lerngruppe.objects.filter(lehrer = lehrer_id)
        gruppen = gruppen.exclude(temp=True)
    except:
        return render(req, 'schueler/keine_gruppe.html', {'titel': "e Schule"})
    return render(req, 'schueler/gruppe_wahl.html', context={ 'gruppen': gruppen, 'lehrer': lehrer, 'titel': "Lerngruppe wählen"})

def gruppe_wahl(req, gruppe_id):
    if not req.user.is_authenticated:
        return redirect('anmelden')  
    schueler = get_object_or_404(Profil, user = req.user)
    try:
        gruppe = get_object_or_404(Lerngruppe, pk = gruppe_id)
        schueler.lerngruppe = gruppe
        schueler.save()
    except:
        return render(req, 'schueler/keine_gruppe.html', context={'titel': "e Gruppe"})
    schueler.gruppe = gruppe
    schueler.save()
    return render(req, 'schueler/gruppe_fertig.html', context={'gruppe': gruppe, 'titel': "fertig!"})

def gruppe_fertig(req, gruppe_id):
    return HttpResponse(gruppe_id)

#für Lehrer
def profil_lehrer(req):
    if User.objects.filter(pk=req.user.id, groups__name='Lehrer').exists():
        lehrer = Profil.objects.get(user=req.user)
        profil_form = Lehrer_Aendern_Form(instance=lehrer,)
        if req.method == 'POST': 
            profil_form = Lehrer_Aendern_Form(req.POST, instance=lehrer)
            if  profil_form.is_valid():
                profil_form.save()
                jg = profil_form.cleaned_data['jg']
                kurs = profil_form.cleaned_data['kurs']
                #lehrer.stufe = stufe_aus_jg(jg, kurs)                       # sorgt dafür, dass Stufe zu Jg und Kurs passt
                lehrer.stufe = profil_form.cleaned_data['stufe']    # mit dieser Zeile kann man die Stufe ohne Vorgaben ändern
                lehrer.save()
                return render(req, 'lehrer/aendern_fertig.html')                            
        context = {'profil_form': profil_form, 'lehrer': lehrer, 'titel': "Profil"}
        return render(req, 'lehrer/profil_lehrer.html', context)
    else:
        return HttpResponse("Zugriff verweigert")

def aufgaben_loeschen(req, lehrer_id):
    if User.objects.filter(pk=req.user.id, groups__name='Lehrer').exists():
        try:
            profil = get_object_or_404(Profil, id=lehrer_id)
        except:
            return HttpResponse("Zugriff verweigert")
        if req.method == 'POST':
            bestaetigt = req.POST.get('bestaetigt', 'off')        
            if bestaetigt == "on":
                Zaehler.objects.filter(profil=profil).delete()
                Protokoll.objects.filter(profil=profil).delete()                
                return render(req, 'lehrer/aendern_fertig.html', {'titel': "Aufgaben wurden gelöscht"})
            return render(req, 'lehrer/aufgaben_loeschen.html', context={'lehrer': profil, 'titel': "wirklich löschen?"}) 
        return render(req, 'lehrer/aufgaben_loeschen.html', context={'lehrer': profil,'titel': "Aufgaben löschen",}) 
    else:
        return HttpResponse("Zugriff verweigert")

def meine_gruppen(req):
    if not User.objects.filter(pk=req.user.id, groups__name='Lehrer').exists():
        return HttpResponse("Zugriff verweigert")  
    else:      
        if req.user.is_superuser:
            gruppen = Lerngruppe.objects.all().order_by("lehrer__profil__nachname")
            super = True
        else:
            gruppen = Lerngruppe.objects.filter(lehrer=req.user)
            super = None
        return render(req, 'lehrer/meine_gruppen.html', context={'gruppen': gruppen, 'titel': "meine Lerngruppen", 'super': super})

def protokoll_zeit_filter(protokoll, auswahl):
    sj, hj = name_hj()
    next_sj, next_hj = name_next_hj()
    if auswahl == "next":
        protokoll = protokoll.filter(sj=next_sj, hj=next_hj)  
    elif auswahl == "Halbjahr":
        protokoll = protokoll.filter(sj=sj, hj=hj)                               
    elif auswahl == "heute":
        protokoll = protokoll.filter(start__date = date.today())
    elif auswahl == "Woche":
        protokoll =  protokoll.filter(start__date__gte = date.today() - timedelta(days = 7))
    # elif auswahl == "8 Tage":
    #     protokoll =  protokoll.filter(start__date__gte = date.today() - timedelta(days = 8))    
    # elif auswahl == "9 Tage":
    #     protokoll =  protokoll.filter(start__date__gte = date.today() - timedelta(days = 9))    
    elif auswahl =="Schuljahr":
        protokoll = protokoll.filter(sj = sj) 
    return protokoll

def gruppe_uebersicht(req, gruppe_id):
    gruppe = get_object_or_404(Lerngruppe, pk=gruppe_id)
    if gruppe.temp:
        req.session['gruppe_id'] = gruppe_id 
        return redirect('duell_uebersicht', gruppe_id)
    from core.views import soll_berechnung, bewertung_kat, bewertung_hj
    sj, hj = name_hj()
    jg = gruppe.jg
    aufgaben_pro_woche = gruppe.aufgaben_pro_woche
    if aufgaben_pro_woche < 1:
        aufgaben_pro_woche = 10 * jg
    if gruppe.lehrer != req.user and not req.user.is_superuser:
        return HttpResponse("Zugriff verweigert")
    titel = f"{gruppe.name}, {gruppe.lehrer.profil.vorname} {gruppe.lehrer.profil.nachname}"
    gesamtzeit_text = ""
    if gruppe.name != "keine Gruppe":
        protokoll_basis = Protokoll.objects.filter(profil__gruppe = gruppe)
    else:
        protokoll_basis = Protokoll.objects.filter(profil__gruppe = None)
    if req.method == 'POST':
        form_filter = ProtokollFilter_neu(req.POST)
        if form_filter.is_valid():
            auswahl_wert = form_filter.cleaned_data['auswahl']
            if auswahl_wert == "individuell":
                wahl = "individuelle Auswahl"
                if 'aufgaben_seit' in req.POST:
                    startdatum_form = Start_Datum(req.POST)
                    enddatum_form = End_Datum(req.POST)
                    if startdatum_form.is_valid() and enddatum_form.is_valid():
                        von = startdatum_form.cleaned_data['aufgaben_seit']
                        bis = enddatum_form.cleaned_data['aufgaben_bis']
                        protokoll_gruppe = protokoll_basis.filter(start__date__range=[von, bis])
                    else:
                        protokoll_gruppe = protokoll_basis.filter(start__date=date.today())
                else:
                    startdatum_form = Start_Datum()
                    enddatum_form = End_Datum()
                    protokoll_gruppe = protokoll_basis.filter(start__date=date.today())
            else:
                choices = form_filter.fields['auswahl'].choices
                wahl = dict(choices)[auswahl_wert]
                if auswahl_wert == "Halbjahr":
                    wahl = "aktuelles Halbjahr"
                startdatum_form = Start_Datum()
                enddatum_form = End_Datum()
                protokoll_gruppe = protokoll_zeit_filter(protokoll_basis, auswahl_wert)
        else:
            wahl = "aktuelles Halbjahr"
            form_filter = ProtokollFilter_neu(initial={'auswahl': 'Halbjahr'})
            startdatum_form = Start_Datum()
            enddatum_form = End_Datum()
            protokoll_gruppe = protokoll_zeit_filter(protokoll_basis, "Halbjahr")
    else:
        wahl = "aktuelles Halbjahr"
        form_filter = ProtokollFilter_neu(initial={'auswahl': 'Halbjahr'})
        startdatum_form = Start_Datum()
        enddatum_form = End_Datum()
        protokoll_gruppe = protokoll_zeit_filter(protokoll_basis, "Halbjahr")
    schulwoche, woche_halbjahr, soll_hj, soll_kat, pflicht_kat = soll_berechnung(sj, hj, jg, aufgaben_pro_woche, gruppe.erstellt_am)
    prozent_summe = 0
    prozent_summe_farbe = False
    richtig_gesamt = falsch_gesamt = 0
    katmax_max = protokoll_gruppe.aggregate(Max('kategorie__zeile'))['kategorie__zeile__max']
    note_anzeigen = True if wahl == "aktuelles Halbjahr" else False
    kategorien = []
    aufgaben_der_schueler = []
    kategorie_summen = [(0, "-")]
    gesamtzeit_text = "-"
    if not katmax_max:
        katmax_max = 0
    if protokoll_gruppe.count() > 0:
        kategorien = list(Kategorie.objects.filter(zeile__lt=katmax_max + 1).order_by('zeile', 'pk'))
        kategorie_summen = [(0, "-")] * (katmax_max+1) 
        kategorie_fehler = [(0)] * (katmax_max+1) 
        gesamtzeit = timedelta()
        if gruppe.name != "keine Gruppe":
            schueler_liste = Profil.objects.filter(gruppe=gruppe).order_by("vorname")
        else:
            schueler_liste = (Profil.objects.filter(gruppe__isnull=True).order_by("vorname"))
        for profil in schueler_liste:
            richtig_profil = falsch_profil = 0
            hj_stimmt = profil.sj == sj and profil.hj == hj
            protokoll_profil = protokoll_gruppe.filter(profil = profil)
            summen = (
                protokoll_profil
                .values("profil")
                .annotate(zeit_profil=Sum(F('end') - F('start')))
            ) 
            dauer_text = "0:00"
            for g in summen:
                dauer = g['zeit_profil']
                try:
                    seconds = int(dauer.total_seconds())
                    mm = int(seconds/60)
                    hh, mm = divmod(mm, 60)
                    dauer_text = f"{hh}:{mm:02d}" 
                    gesamtzeit = gesamtzeit + dauer
                except:
                    dauer_text = "---"
            aufgaben = [(0, "-")] * (katmax_max+1)
            kategorie_werte = (
                protokoll_profil
                .values("kategorie__zeile")
                .annotate(richtig_kat=Sum(
                    Case(
                        When(richtig=True, then=1),
                        default=0,
                        output_field=IntegerField(),
                    )
                ),)
            )
            for k in kategorie_werte:
                index = int(k['kategorie__zeile'])
                richtig_kat = k['richtig_kat']
                kat_name = Kategorie.objects.get(zeile = index)
                falsch_kat = lsg_kat = abbr_kat = 0
                zaehler = Zaehler.objects.filter(profil = profil, kategorie = kat_name)
                protokoll_profil_fehler = protokoll_gruppe.filter(profil = profil)
                protokoll_profil_kategorie = protokoll_profil_fehler.filter(kategorie = kat_name)
                if zaehler.count() == 0:
                    fehler, created = Geloescht.objects.get_or_create(benutzername = str(profil.user))
                    if created:
                        fehler.text = "folgende Zählerobjekte wurden angelegt: "
                        fehler.text += str(kat_name)+ ", "
                        fehler.grund = "Zähler angelegt"
                    else:
                        fehler.text += str(kat_name)+ ", "
                else:
                    zaehler = zaehler.first()
                    richtig_gesamt += richtig_kat
                    if wahl == "aktuelles Halbjahr":
                        falsch_kat = zaehler.fehler_zaehler
                        lsg_kat = zaehler.lsg_zaehler
                        abbr_kat = zaehler.abbr_zaehler
                        hilfe_kat = zaehler.hilfe_zaehler  
                    else:
                        fehler_ab = zaehler.fehler_ab
                        protokoll_fehler = protokoll_profil_kategorie.filter(start__gt=fehler_ab)
                        protokoll_fehler = (
                            protokoll_fehler
                            .values("kategorie__zeile")
                            .annotate(
                                falsch_kat=Sum(Case(When(falsch=True, then=1), default=0, output_field=IntegerField())),
                                abbr_kat=Sum(Case(When(abbr=True, then=1), default=0, output_field=IntegerField())),
                                lsg_kat=Sum(Case(When(lsg=True, then=1), default=0, output_field=IntegerField())),
                                hilfe_kat=Sum(Case(When(hilfe=True, then=1), default=0, output_field=IntegerField())),
                            )
                        )
                        for f in protokoll_fehler:
                            falsch_kat = f['falsch_kat'] 
                            abbr_kat = f['abbr_kat']
                            lsg_kat = f['lsg_kat'] 
                            hilfe_kat = f['hilfe_kat'] 
                            if abbr_kat == True:
                                abbr_kat = 1
                            elif abbr_kat == False:
                                abbr_kat = 0 
                            if lsg_kat == True:
                                lsg_kat = 1
                            elif lsg_kat == False:
                                lsg_kat = 0 
                            if hilfe_kat == True:
                                hilfe_kat = 1
                            elif hilfe_kat == False:
                                hilfe_kat = 0 
                richtig_profil += richtig_kat
                falsch_profil += falsch_kat
                kategorie_fehler[index] += falsch_kat
                quote = quote_farbe(richtig_kat, falsch_kat)
                aufgaben[index] = (quote, richtig_kat)
                prozent_kat, prozent_kat = bewertung_kat(soll_kat, richtig_kat, falsch_kat, lsg_kat, abbr_kat, profil.stufe)
                prozent_summe += prozent_kat
            prozent_summe_farbe, prozent_summe, note = bewertung_hj(prozent_summe, pflicht_kat, profil.stufe, False)
            if soll_hj < 10*pflicht_kat and prozent_summe < 50:
                note = "-"
                prozent_summe_farbe = None
            quote_profil = quote_farbe(richtig_profil, falsch_profil)
            aufgaben[0] = (quote_profil, int(richtig_profil))
            aufgaben_der_schueler.append((
                profil, hj_stimmt, prozent_summe_farbe, prozent_summe, note, dauer_text, aufgaben
            ))
        seconds = int(gesamtzeit.total_seconds())
        mm = int(seconds/60)
        hh, mm = divmod(mm, 60)
        gesamtzeit_text = f"{hh}:{mm:02d}" 
        gesamtsummen = (
            protokoll_gruppe
            .values("kategorie__zeile")
            .annotate(richtig_sum=Sum(Case(When(richtig=True, then=1), default=0, output_field=IntegerField())))
            .annotate(zeit_sum=Sum(F('end') - F('start')))
        ) 
        for k in gesamtsummen: 
            index = int(k['kategorie__zeile'])
            richtig_sum = k['richtig_sum']
            quote = quote_farbe(richtig_sum, kategorie_fehler[index])
            kategorie_summen[index] = (quote, richtig_sum)
    quote_gesamt = quote_farbe(richtig_gesamt, falsch_gesamt)
    kategorie_summen[0] = (quote_gesamt, int(richtig_gesamt))
    context = {
        'gruppe': gruppe, 'gruppe_id': gruppe_id, 'wahl': wahl, 
        'aufgaben_der_schueler': aufgaben_der_schueler, 'kategorien': kategorien, 
        'titel': titel, 'summen': kategorie_summen, 'gesamtzeit': gesamtzeit_text,
        'note_anzeigen': note_anzeigen,
        'form_filter': form_filter,      
        'startdatum': startdatum_form,   
        'enddatum': enddatum_form,       
    }  
    return render(req, 'lehrer/gruppe_uebersicht.html', context)

def neue_gruppe(req):
    if User.objects.filter(pk=req.user.id, groups__name='Lehrer').exists():
        gruppe_neu = Gruppe_Neu_Form() 
        if req.method == 'POST':
            gruppe_form = Gruppe_Neu_Form(req.POST) 
            if  gruppe_form.is_valid():
                gruppen = Lerngruppe.objects.filter(lehrer=req.user).order_by('name')
                neu = gruppe_form.cleaned_data['name']
                jg = gruppe_form.cleaned_data['jg']
                aufgaben = gruppe_form.cleaned_data['aufgaben_pro_woche']
                gruppe, created = Lerngruppe.objects.get_or_create(name = neu, lehrer = req.user, jg = jg, aufgaben_pro_woche = aufgaben)
                if not created:
                    return render(req, 'lehrer/neue_gruppe.html', context={'gruppe': gruppe_form, 'titel': "Ein Gruppe mit diesem Name existiert schon!",})                 
                return render(req, 'lehrer/meine_gruppen.html', context={'gruppen': gruppen, 'titel': "neue Lerngruppe wurde angelegt"}) 
        return render(req, 'lehrer/neue_gruppe.html', context={'gruppe_neu': gruppe_neu, 'titel': "neue Lerngruppe anlegen",})
    else:
        return HttpResponse("Zugriff verweigert")
    
def gruppe_aendern(req, gruppe_id):
    gruppe = get_object_or_404(Lerngruppe, pk=gruppe_id)
    if gruppe.lehrer != req.user and not req.user.is_superuser:
        return HttpResponse("Zugriff verweigert")
    if req.method == 'POST':
        gruppe_form = Gruppe_Aendern_Form(req.POST, instance=gruppe)
        if gruppe_form.is_valid():
            gruppe_form.save()
            gruppen = Lerngruppe.objects.filter(lehrer=req.user)
            return render(req, 'lehrer/meine_gruppen.html', context={'gruppen': gruppen,'titel': "Daten wurden geändert"}) 
        else:
            return HttpResponse("Entschuldigung, das hat nicht geklappt!")
    else:
        gruppe_form = Gruppe_Aendern_Form(instance=gruppe,)
        context={'gruppe_form': gruppe_form, 'gruppe': gruppe, 'titel': "Daten der Lerngruppe ändern",}
        return render(req, 'lehrer/gruppe_aendern.html', context) 

def gruppe_loeschen(req, gruppe_id):
    gruppe = Lerngruppe.objects.get(pk = gruppe_id)
    if gruppe.lehrer != req.user:
        return HttpResponse("Zugriff verweigert")
    if req.method == 'POST':
        bestaetigt = req.POST.get('bestaetigt', 'off')        
        if bestaetigt == "on":
            gruppe.delete()
            gruppen = Lerngruppe.objects.filter(lehrer=req.user)
            return render(req, 'lehrer/meine_gruppen.html', context={'gruppen': gruppen, 'titel': "Gruppe wurde gelöscht!"}) 
        return render(req, 'lehrer/gruppe_loeschen.html', context={'gruppe': gruppe, 'titel': "wirklich löschen?"}) 
    return render(req, 'lehrer/gruppe_loeschen.html', context={'gruppe': gruppe, 'titel': "Gruppe löschen",}) 

def mein_schueler(req, schueler_id, hj_stimmt):
    mein_schueler = get_object_or_404(Profil, id=schueler_id)
    if not req.user.is_superuser:
        try:
            if mein_schueler.gruppe.lehrer != req.user: 
                return HttpResponse("Zugriff verweigert")
        except:
            return HttpResponse("keine Daten vorhanden")
    try:
        gruppe = mein_schueler.gruppe
        titel = str(gruppe.name) + ": " + str(mein_schueler.vorname) + " " + str(mein_schueler.nachname)
    except:
        gruppe = get_object_or_404(Lerngruppe, name = "keine Gruppe")
        titel = str(mein_schueler) + " keine Gruppe"
    context={'titel': titel,'schueler': mein_schueler, 'gruppe': gruppe, 'aktuelles_hj': hj_stimmt}
    return render(req, 'lehrer/mein_schueler.html', context) 

def schueler_aendern(req, schueler_id):
    schueler = Profil.objects.get(id=schueler_id)
    if schueler.gruppe.lehrer != req.user and not req.user.is_superuser:
        return HttpResponse("Zugriff verweigert")
    if req.method == 'POST': 
        profil_form = Schueler_Aendern_Form(req.POST, instance=schueler)
        if  profil_form.is_valid():
            profil_form.save()
            jg = profil_form.cleaned_data['jg']
            kurs = profil_form.cleaned_data['kurs']
            schueler.stufe = stufe_aus_jg(jg, kurs)
            schueler.save() 
            return render(req, 'lehrer/aendern_fertig.html', {'titel': "Daten wurden geändert"})
        else:
            return HttpResponse("Entschuldigung, das hat nicht geklappt!")
    profil_form = Schueler_Aendern_Form(instance=schueler,)
    context = {'profil_form': profil_form, 'schueler': schueler, 'titel': "Schülerdaten ändern"}
    return render(req, 'lehrer/schueler_aendern.html', context)

def suchen(req, gruppe_id=None):
    if not req.user.is_authenticated:
        return redirect('anmelden')  
    if User.objects.filter(pk=req.user.id, groups__name='Lehrer').exists() or req.user.is_superuser:
        vorname = nachname = nachricht = ""
        if not gruppe_id: 
            profile = Profil.objects.filter(gruppe = None).order_by('vorname','nachname')
            profile = profile.filter(~Q(user__groups__name = 'Lehrer'))
        else:
            gruppe = Lerngruppe.objects.get(id = gruppe_id)
            if gruppe.name == "keine Gruppe" or gruppe_id == None:
                profile = Profil.objects.filter(gruppe = None).order_by('vorname','nachname')
                profile = profile.filter(~Q(user__groups__name = 'Lehrer'))
            else:
                profile = Profil.objects.filter(gruppe_id = gruppe_id).order_by('vorname','nachname')
        zeilen = []   
        sj, hj = name_hj()
        for profil in profile:
            gesamt = Protokoll.objects.filter(profil_id = profil.id)
            neu = gesamt.filter(sj = sj, hj = hj)
            zeilen.append((profil, gesamt.count, neu.count))
        profil = None
        if req.method == "POST":
            zusammen_form = Zusammen_Form(req.POST)
            if zusammen_form.is_valid():
                quelle = zusammen_form.cleaned_data['quelle']
                ziel = zusammen_form.cleaned_data['ziel']
                if ziel  and quelle :
                    user_quelle, nachricht_quelle = account_pruefen(quelle)
                    user_ziel,  nachricht_ziel= account_pruefen(ziel)
                    nachricht = nachricht_quelle + " - " + nachricht_ziel
                    if len(nachricht) < 5:
                        gruppe = user_quelle.profil.gruppe
                        if gruppe == None or gruppe.id != gruppe_id:
                            nachricht_quelle = " Der user mit der ID {} ist nicht Ihrer Lerngruppe zugeordnet".format(quelle) 
                        else:
                            vorname_quelle = user_quelle.profil.vorname 
                            nachname_quelle = user_quelle.profil.nachname 
                        gruppe = user_ziel.profil.gruppe
                        if gruppe == None or gruppe.id != gruppe_id:
                            nachricht_ziel = " Der user mit der ID {} ist nicht Ihrer Lerngruppe zugeordnet".format(ziel) 
                        else:
                            vorname_ziel = user_ziel.profil.vorname 
                            nachname_ziel = user_ziel.profil.nachname 
                        nachricht = nachricht_quelle + " - " + nachricht_ziel
                        if len(nachricht) < 5:
                            if  not req.user.is_superuser and (vorname_quelle.upper() != vorname_ziel.upper() or nachname_quelle.upper() != nachname_ziel.upper()):  
                                nachricht = "Die Namen stimmen nicht überein!"
                            else:
                                protokolle = Protokoll.objects.filter(profil = user_quelle.profil)
                                if protokolle.count() == 0:
                                    nachricht = "Es sind keine Aufgaben zum Übertragen da."
                                else:
                                    user = User.objects.get(id = user_quelle.id)
                                    verschoben, created = Geloescht.objects.get_or_create(benutzername = str(user))
                                    heute = date.today()
                                    zaehler_quelle = Zaehler.objects.filter(profil = user_quelle.profil)
                                    nachricht = "Der/die Zähler: "
                                    for q in zaehler_quelle:
                                        ziele = Zaehler.objects.filter(profil = user_ziel.profil, kategorie = q.kategorie)
                                        if ziele.count() == 0:
                                            nachricht = nachricht + '"' + str(q.kategorie) + '", '
                                            q.profil = user_ziel.profil
                                            q.save()
                                        else:
                                            ziel = ziele.first()
                                            if  ziel.sj >0 and ziel.sj == q.sj and ziel.hj == q.hj:
                                                ziel.fehler_zaehler += q.fehler_zaehler
                                                ziel.abbr_zaehler += q.abbr_zaehler
                                                ziel.lsg_zaehler += q.lsg_zaehler
                                                ziel.hilfe_zaehler += q.hilfe_zaehler
                                                if ziel.richtig_of < q.richtig_of:
                                                    ziel.richtig_of = q.richtig_of
                                                if ziel.letzte < q.letzte:
                                                    ziel.letzte = q.letzte
                                                ziel.save()
                                            q.delete() 
                                    if nachricht != "Der/die Zähler: ":
                                        nachricht += ' wurde(n) am {} von Account "{}" übernommen.<br>'.format(heute, user_quelle.profil)
                                        verschoben.text += nachricht
                                        verschoben.grund = "zaehler_verschoben"
                                        verschoben.save()
                                    n = 0
                                    for protokoll in protokolle:
                                        n += 1
                                        protokoll.profil = user_ziel.profil
                                        protokoll.anmerkung = "übertragen von user ID: ", quelle
                                        protokoll.save()
                                    nachricht = 'am {} wurden {} Aufgaben von Account "{}" auf Account "{}" übertragen.'.format(heute, n, user_quelle.profil, user_ziel.profil)
                                    verschoben.text += nachricht
                                    verschoben.save()                  
            abmelden_form = Abmelden_Form(req.POST)
            if abmelden_form.is_valid():
                abmelden = abmelden_form.cleaned_data['abmelden']
                if abmelden:
                    user, nachricht = account_pruefen(abmelden)
                    if len(nachricht) < 5:
                        gruppe = user.profil.gruppe
                        if gruppe == None or gruppe.id != gruppe_id:
                            nachricht = " Der user mit der ID {} ist nicht Ihrer Lerngruppe zugeordnet".format(abmelden) 
                        else:
                            nachricht = 'Das Userprofil von {} mit dem Account "{}" wurde aus der Lerngruppe {} entfernt'.format(user.profil.vorname+" "+user.profil.nachname, user.username, gruppe)
                            user.profil.gruppe = None
                            user.profil.save()
            loeschen_form = Loeschen_Form(req.POST)
            if loeschen_form.is_valid():
                loeschen = loeschen_form.cleaned_data['loeschen']
                if loeschen:
                    user, nachricht = account_pruefen(loeschen)
                    if len(nachricht) < 5:
                        gruppe = user.profil.gruppe
                        if gruppe == None or gruppe.id != gruppe_id:
                            nachricht = " Der user mit der ID {} ist nicht Ihrer Lerngruppe zugeordnet".format(loeschen) 
                        else:
                            protokolle = Protokoll.objects.filter(profil = user.profil.id) 
                            if protokolle.count() > 0:
                                nachricht = 'Mit dem Account "{}"  von {} wurden schon {} Aufgaben gerechnet, die müssen zuerst übertragen werden!'.format(user, profil.vorname+" "+profil.nachname, protokolle.count())
                            else:
                                user.groups.clear()
                                user.delete()
                                heute = date.today()
                                nachricht = 'Das Userprofil von {} mit dem Account "{}" wurde am {} von {} {} gelöscht.'.format(user.profil.vorname+" "+user.profil.nachname, user.username, heute, req.user.profil.vorname, req.user.profil.nachname)
                                geloescht, created = Geloescht.objects.get_or_create(benutzername = str(user))
                                geloescht.text += nachricht
                                geloescht.text = "profil_gelöscht"
                                geloescht.save()
        loeschen_form = Loeschen_Form
        zusammen_form = Zusammen_Form
        abmelden_form = Abmelden_Form
        context = {"abmelden_form": abmelden_form, "loeschen_form": loeschen_form, "zusammen_form": zusammen_form, "zeilen" : zeilen, "nachricht": nachricht, 'titel': "Accounts löschen", "gruppe_id": gruppe_id}
        return render(req, 'admin/suchen.html', context)
    else:
        return HttpResponse("Zugriff verweigert")

def account_pruefen(id):
    nachricht = ""
    user = User.objects.filter(id = id).first()
    if user == None:
        nachricht = "Ein Account mit der ID {} existiert nicht".format(id)
    else:
        profil = Profil.objects.filter(user = user).first()
        if profil == None:
            nachricht = "Ein Profil mit der ID {} existiert nicht".format(id)
    return user, nachricht