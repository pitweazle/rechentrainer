import os
import string
import random
import hashlib
import json
import logging
logger = logging.getLogger(__name__)

import base64
import requests

import urllib.parse

from datetime import date, datetime, timedelta, time

from decimal import Decimal

from itertools import groupby

from pathlib import Path

from django.core.mail import send_mail

from django.utils import timezone

from django.shortcuts import render, redirect, get_object_or_404

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User, Group
from django.contrib.sessions.models import Session

from django.http import HttpResponse, HttpResponseBadRequest, HttpRequest , QueryDict, FileResponse, Http404, request
from django.conf import settings

from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from django.db.models import Max, Sum, Count, F, Q, Prefetch
from django.db.models import Sum, Case, When, IntegerField
from django.db import connection

from .forms import Register_Form, Profil_Form, Login_Form, Suchen_Form, Loeschen_Form, Zusammen_Form, Abmelden_Form
from .forms import Profil_Aendern_Form, Ort_Form, Lehrer_Aendern_Form, Gruppe_Neu_Form, Gruppe_Aendern_Form, Schueler_Aendern_Form 
from .forms import ProtokollFilter_neu, Start_Datum, End_Datum

from .models import Profil, Schule, Ort, Lerngruppe, Geloescht, wahl_kurs, LoginLog, wahl_kurs
from .services import get_today, check_hj, stufe_aus_jg, sub_daten_loeschen, name_hj, name_next_hj, quote_farbe

from core.models import Zaehler, Profil, Kategorie, Protokoll, EwigeBestenliste
from core.views import soll_berechnung

from mathetests.models import Test

# Konfigurationswerte
EDUPLACES_CLIENT_ID = "5102a595-d3d4-4150-b868-9fcbe40f23df"
EDUPLACES_CLIENT_SECRET = os.getenv("EDUPLACES_CLIENT_SECRET")
EDUPLACES_REDIRECT_URI = "https://rechentrainer.app/eduplaces/callback/"
OIDC_CONFIG_URL = "https://auth.sandbox.eduplaces.dev/.well-known/openid-configuration"

EDUPLACES_DUELL_CLIENT_ID = "d0dce1cc-7ffc-4854-b19c-d60bd81f870a"
EDUPLACES_DUELL_CLIENT_SECRET = os.getenv("EDUPLACES_DUELL_CLIENT_SECRET")
EDUPLACES_DUELL_REDIRECT_URI = "https://rechentrainer.app/eduplaces_duell/callback/"

# Dies ist die Startseite:
def index(req):
    if 'duell' in req.session:
        del req.session['duell']
    # Prüfen, ob Eduplaces uns einen Login aufzwingen will (Launch aus dem Portal)
    iss = req.GET.get('iss')
    login_hint = req.GET.get('login_hint')
    if iss and login_hint:
        # Parameter für den Eduplaces-Login zusammenbauen und direkt dorthin weiterleiten
        auth_endpoint, _, _ = get_oidc_endpoints() # Deine bestehende Funktion
        
        state = secrets.token_urlsafe(16)
        req.session['eduplaces_state'] = state
        
        scopes = (
            "openid role groups school schooling_level school_name"
            " school_location school_official_id"
            " profile"
        )
        
        params = {
            'response_type': 'code',
            'client_id': EDUPLACES_CLIENT_ID,
            'redirect_uri': EDUPLACES_REDIRECT_URI,
            'scope': scopes,
            'state': state,
            'iss': iss,
            'login_hint': login_hint,
        }       
        
        redirect_url = f"{auth_endpoint}?{urllib.parse.urlencode(params)}"
        return redirect(redirect_url)

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
        if not profil or not profil.mathe or not profil.sj:
            return redirect('rt_profil_ergaenzen')
        if profil and profil.gruppe_id:
            tests = Test.objects.filter(gruppe = profil.gruppe).order_by("-created_at")
    else:
        profil = None
    return render(req, "mathe_start.html", {"profil": profil, "lehrer": lehrer, "anz_angemeldet": anz_angemeldet, "anz_lehrer": anz_lehrer, "anz_aufg": anz_gesamt, "tests": tests, })

def rt_profil_ergaenzen(request):
    user = request.user
    # Profil holen oder anlegen, falls noch keines da ist
    profil, created = Profil.objects.get_or_create(user=user)
    
    if request.method == 'POST':
        aktion = request.POST.get('aktion')
        if aktion == 'registrierung_speichern':
            # Namen auslesen (falls leer gewesen, wurden sie im Template als required abgefragt)
            eingabe_vorname = request.POST.get('reg_vorname', '').strip()
            eingabe_nachname = request.POST.get('reg_nachname', '').strip()
            
            if eingabe_vorname:
                profil.vorname = eingabe_vorname
            if eingabe_nachname:
                profil.nachname = eingabe_nachname
                
            profil.klasse = request.POST.get('reg_klasse')
            
            reg_jg = int(request.POST.get('reg_jg'))
            reg_kurs = request.POST.get('reg_kurs')
            reg_email = request.POST.get('reg_email')
            
            # E-Mail am Standard-User aktualisieren, falls angegeben
            if reg_email and not user.email:
                user.email = reg_email
                user.save()
            
            # 1. Mathe-Berechtigung aktivieren & Stufe berechnen
            profil.mathe = True  
            profil.stufe = stufe_aus_jg(reg_jg, reg_kurs)
            
            # 2. Schuljahr und Halbjahr über deine Service-Funktion setzen
            sj, hj = name_hj()
            profil.sj = sj
            profil.hj = hj
            
            # Zeitstempel für den Beginn setzen, falls noch leer
            if not profil.schuljahr_ab and not profil.halbjahr_ab:
                heute_datum = get_today()
                if hj == 1:
                    profil.schuljahr_ab = timezone.now()
                else:
                    profil.halbjahr_ab = timezone.now()
                    
            profil.save()
            ergebnis = check_hj(request)
            if ergebnis:
                return ergebnis
            return redirect('ort_wahl')

    # Kontext für das Template bereitstellen
    # Prüfen, ob der Benutzer ein Lehrer ist
    is_lehrer = User.objects.filter(pk=user.id, groups__name='Lehrer').exists()
    
    context = {
        'moodle_vorname': profil.vorname,   
        'moodle_nachname': profil.nachname, 
        'moodle_email': user.email,
        'kurs_choices': wahl_kurs.choices,
        'titel': "Registrierung abschließen",
        'is_lehrer': is_lehrer,
        'form_klasse': 'Lehrer' if is_lehrer else profil.klasse if profil.klasse else '',
        'form_jg': profil.jg if profil.jg else 5,
        'rollen_label': 'Rolle (z.B. Lehrer / Lehrerin):' if is_lehrer else 'Klasse:',
        'rollen_placeholder': 'z.B. Lehrer' if is_lehrer else 'z.B. 6R',
        'platform': 'mathe',
    }
    return render(request, 'SSO/sso_registrierung.html', context)

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
                profil.mathe = True
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

def custom_logout(request):
    logout(request)
    return redirect('index')

# moodle:
@csrf_exempt
def lti_launch(request):
    if request.method != 'POST':
        return HttpResponseBadRequest("Nur POST-Anfragen erlaubt.")

    platform = request.platform  # 'mathe' oder 'physik' – von der Middleware gesetzt

    consumer_key = request.POST.get('oauth_consumer_key')
    try:
        schule_obj = Schule.objects.get(dienststellen_nr=consumer_key)
    except Schule.DoesNotExist:
        return HttpResponseBadRequest(f"Unbekannte Dienststellennummer: '{consumer_key}'.")

    logger = logging.getLogger(__name__)
    logger.warning(f"MOODLE POST DATEN ({platform}): {request.POST.dict()}")

    moodle_uid = request.POST.get('user_id')
    vorname = request.POST.get('lis_person_name_given', '').strip()
    nachname = request.POST.get('lis_person_name_family', '').strip()
    moodle_email = request.POST.get('lis_person_contact_email_primary', '').strip()
    if moodle_email.endswith('.invalid'):
        moodle_email = ''
    moodle_rollen = request.POST.get('roles', 'Learner')

    LoginLog.objects.create(
        quelle=f'moodle_{platform}',
        consumer_key=consumer_key,
        user_id=moodle_uid,
        user_name=request.POST.get('lis_person_name_full'),
        rolle=moodle_rollen,
        institution_name=request.POST.get('tool_consumer_instance_name'),
        rohdaten=str(request.POST.dict())
    )

    if 'Instructor' in moodle_rollen or 'Teacher' in moodle_rollen:
        ziel_gruppen_name = "Lehrer"
    else:
        ziel_gruppen_name = "Schüler"

    if not moodle_uid or not vorname or not nachname:
        return HttpResponseBadRequest("Falsche oder unvollständige Moodle-Daten übermittelt.")

    # WENN ID SCHON IM PROFIL -> Einloggen
    try:
        #profil = Profil.objects.get(moodle_uid=moodle_uid)
        profil = Profil.objects.get(moodle_uid=moodle_uid, schule=schule_obj)
        user = profil.user
        gruppe_obj = Group.objects.filter(name=ziel_gruppen_name).first()
        if gruppe_obj:
            user.groups.add(gruppe_obj)
        if moodle_email and user.email != moodle_email:
            user.email = moodle_email
            user.save()
        login(request, user)
        return redirect('physik:index' if platform == 'physik' else 'index')
    except Profil.DoesNotExist:
        pass

    # WENN KEINE ID, ABER NAME STIMMT ÜBEREIN -> ID eintragen und einloggen
    profil = Profil.objects.filter(vorname=vorname, nachname=nachname, schule=schule_obj).first()
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
        return redirect('physik:index' if platform == 'physik' else 'index')

    # WENN KEINE ID UND KEINE NAMENSÜBEREINSTIMMUNG -> Daten merken und ab zur Frage!
    request.session['moodle_launch_data'] = {
        'moodle_uid': moodle_uid,
        'vorname': vorname,
        'nachname': nachname,
        'email': moodle_email,
        'schule_id': schule_obj.id,
        'gruppe': ziel_gruppen_name,
        'platform': platform,   # ← neu: mitnehmen für den nächsten Schritt
        'jg': request.POST.get('custom_jg', request.POST.get('jg', 5)),
        'klasse': request.POST.get('context_title', 'Moodle-Kurs')[:10]
    }
    return redirect('moodle_entscheidung')

@csrf_exempt
def moodle_entscheidung(request):
    moodle_data = request.session.get('moodle_launch_data')
    if not moodle_data:
        return redirect('index')
    platform = moodle_data.get('platform', 'mathe')

    if request.method == 'POST':
        aktion = request.POST.get('aktion')
        # A) Registrierungs-Formular anzeigen
        if aktion == 'neu_registrieren':
            default_vorname = moodle_data.get('vorname', '')
            default_nachname = moodle_data.get('nachname', '')
            is_lehrer = (moodle_data.get('gruppe') == 'Lehrer')

            default_jg = ""
            default_klasse = ""

            context = {
                'moodle_vorname': default_vorname,
                'moodle_nachname': default_nachname,
                'moodle_email': moodle_data.get('email', ''),
                'kurs_choices': wahl_kurs.choices,
                'titel': "Registrierung abschließen",
                'is_lehrer': is_lehrer,
                'form_klasse': 'Lehrer' if is_lehrer else '',
                'form_jg': default_jg,
                'rollen_label': "Rolle (z.B. Lehrer / Lehrerin):" if is_lehrer else "Klasse:",
                'rollen_placeholder': 'z.B. Lehrer' if is_lehrer else 'z.B. 6R',
                'platform': platform,
            }
            return render(request, 'SSO/sso_registrierung.html', context)
        
        # Das Formular wurde ausgefüllt abgeschickt -> Jetzt in der DB speichern
        elif aktion == 'registrierung_speichern':
            reg_vorname = request.POST.get('reg_vorname', '').strip()
            reg_nachname = request.POST.get('reg_nachname', '').strip()
            reg_email = request.POST.get('reg_email', '').strip()
            reg_klasse = request.POST.get('reg_klasse', '')[:10]

            if platform == 'mathe':
                reg_jg = request.POST.get('reg_jg', '').strip()
                reg_kurs = request.POST.get('reg_kurs', '').strip()
            else:  # physik
                reg_jg = ''
                reg_kurs = ''

            #username = f"moodle_{moodle_data['moodle_uid'][:20]}"
            schule_obj = Schule.objects.get(id=moodle_data['schule_id'])
            username = f"moodle_{schule_obj.dienststellen_nr}_{moodle_data['moodle_uid'][:20]}"
            zufalls_passwort = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))

            user = User.objects.create_user(username=username, email=reg_email, password=zufalls_passwort)

            gruppe_obj = Group.objects.filter(name=moodle_data['gruppe']).first()
            if gruppe_obj:
                user.groups.add(gruppe_obj)
            sj, hj = name_hj()

            Profil.objects.create(
                user=user,
                moodle_uid=moodle_data['moodle_uid'],
                vorname=reg_vorname,
                nachname=reg_nachname,
                schule=schule_obj,
                jg=reg_jg,
                klasse=reg_klasse,
                kurs=reg_kurs,
                mathe=(platform == 'mathe'),
                sj=sj,
                hj=hj,
                # physik=(platform == 'physik')
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
def simulation_moodle(request):
    if request.method == 'POST':
        q = QueryDict('', mutable=True)
        q.setlist('oauth_consumer_key', [request.POST.get('schule_id', 'DE-HE-6072')])
        q.setlist('user_id', [request.POST.get('uid', 'test_franz')])
        q.setlist('lis_person_name_given', [request.POST.get('vorname', 'Franz')])
        q.setlist('lis_person_name_family', [request.POST.get('nachname', 'Musterschüler')])
        q.setlist('lis_person_contact_email_primary', [request.POST.get('email', 'test@example.de')])
        q.setlist('roles', [request.POST.get('gruppe', 'Learner')])
        q.setlist('context_title', [request.POST.get('klasse', 'Testklasse')])
        q.setlist('custom_jg', [request.POST.get('jg', '6')])

        fake_request = HttpRequest()
        fake_request.method = 'POST'
        fake_request.POST = q
        fake_request.session = request.session
        fake_request.platform = request.platform

        return lti_launch(fake_request)

    return HttpResponse(f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Moodle-LTI-Simulation (realistisch)</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }}
                form {{ background: #f5f5f5; padding: 20px; border-radius: 8px; }}
                input, select, button {{ padding: 8px; margin: 5px 0; width: 100%; box-sizing: border-box; }}
                button {{ background: #28a745; color: white; border: none; cursor: pointer; }}
            </style>
        </head>
        <body>
            <h1>Moodle-LTI-Simulation (für lti_launch)</h1>
            <p>Simuliert eine echte Moodle-LTI-Anfrage an <code>lti_launch</code>.</p>
            <p><strong>Aktuell erkannte Platform:</strong> {request.platform}</p>

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

# Eduplaces:
@csrf_exempt
@require_POST
def eduplaces_logout(request):
    LoginLog.objects.create(
        quelle='eduplaces_logout_debug',
        consumer_key='DIAGNOSE',
        user_id='',
        user_name='Logout-Callback erreicht',
        rolle='',
        institution_name='',
        rohdaten=request.body.decode('utf-8', errors='replace')[:1000]
    )

    logout_token = request.POST.get('logout_token')

    if not logout_token:
        logger.warning("[ED-LOGOUT] Kein logout_token im POST-Body gefunden.")
        return HttpResponse("Missing logout_token", status=400)

    try:
        payload = decode_jwt_payload(logout_token)
        if not payload:
            logger.warning("[ED-LOGOUT] Token konnte nicht dekodiert werden.")
            return HttpResponse("Invalid logout_token", status=400)

        eduplaces_sub = payload.get('sub')
        eduplaces_sid = payload.get('sid')
        logger.warning(f"[ED-LOGOUT] sub={eduplaces_sub!r} sid={eduplaces_sid!r}")

        if not eduplaces_sub and not eduplaces_sid:
            logger.warning("[ED-LOGOUT] Weder 'sub' noch 'sid' im Token-Payload gefunden.")
            return HttpResponse("OK", status=200)

        gefunden = 0
        alle_sessions = list(Session.objects.all())
        logger.warning(f"[ED-LOGOUT] {len(alle_sessions)} Sessions insgesamt in der DB. Suche sid={eduplaces_sid!r}")

        for session in alle_sessions:
            session_data = session.get_decoded()
            gespeicherte_sid = session_data.get('eduplaces_sid')
            gespeicherte_sub = session_data.get('eduplaces_sub')
            if gespeicherte_sid or gespeicherte_sub:
                logger.warning(
                    f"[ED-LOGOUT]   Session {session.session_key[:8]}... "
                    f"expire={session.expire_date} "
                    f"gespeicherte_sid={gespeicherte_sid!r} (type={type(gespeicherte_sid).__name__}) "
                    f"gespeicherte_sub={gespeicherte_sub!r}"
                )

            treffer = False
            if eduplaces_sid and gespeicherte_sid == eduplaces_sid:
                treffer = True
            elif eduplaces_sub and gespeicherte_sub == eduplaces_sub:
                treffer = True

            if treffer:
                gefunden += 1
                key_fuer_log = session.session_key
                session.delete()
                logger.warning(f"[ED-LOGOUT] Session {key_fuer_log[:8]}... gelöscht.")

        logger.warning(f"[ED-LOGOUT] Fertig. {gefunden} Session(s) gelöscht.")
        return HttpResponse("OK", status=200)

    except Exception as e:
        logger.error(f"[ED-LOGOUT] Fehler beim Verarbeiten: {e}", exc_info=True)
        return HttpResponse(f"Error processing logout: {str(e)}", status=400)
    
# @csrf_exempt
# @require_POST
# def eduplaces_logout(request):
#     logout_token = request.POST.get('logout_token')

#     if not logout_token:
#         logger.warning("[ED-LOGOUT] Kein logout_token im POST-Body gefunden.")
#         return HttpResponse("Missing logout_token", status=400)

#     try:
#         payload = decode_jwt_payload(logout_token)
#         if not payload:
#             logger.warning("[ED-LOGOUT] Token konnte nicht dekodiert werden.")
#             return HttpResponse("Invalid logout_token", status=400)

#         eduplaces_sub = payload.get('sub')
#         eduplaces_sid = payload.get('sid')
#         logger.warning(f"[ED-LOGOUT] sub={eduplaces_sub!r} sid={eduplaces_sid!r}")

#         if not eduplaces_sub and not eduplaces_sid:
#             logger.warning("[ED-LOGOUT] Weder 'sub' noch 'sid' im Token-Payload gefunden.")
#             return HttpResponse("OK", status=200)

#         gefunden = 0
#         alle_sessions = list(Session.objects.all())
#         logger.warning(f"[ED-LOGOUT] {len(alle_sessions)} Sessions insgesamt in der DB. Suche sid={eduplaces_sid!r}")

#         for session in alle_sessions:
#             session_data = session.get_decoded()
#             gespeicherte_sid = session_data.get('eduplaces_sid')
#             gespeicherte_sub = session_data.get('eduplaces_sub')
#             if gespeicherte_sid or gespeicherte_sub:
#                 logger.warning(
#                     f"[ED-LOGOUT]   Session {session.session_key[:8]}... "
#                     f"expire={session.expire_date} "
#                     f"gespeicherte_sid={gespeicherte_sid!r} (type={type(gespeicherte_sid).__name__}) "
#                     f"gespeicherte_sub={gespeicherte_sub!r}"
#                 )

#             treffer = False
#             if eduplaces_sid and gespeicherte_sid == eduplaces_sid:
#                 treffer = True
#             elif eduplaces_sub and gespeicherte_sub == eduplaces_sub:
#                 treffer = True

#             if treffer:
#                 gefunden += 1
#                 key_fuer_log = session.session_key
#                 session.delete()
#                 logger.warning(f"[ED-LOGOUT] Session {key_fuer_log[:8]}... gelöscht.")

#         logger.warning(f"[ED-LOGOUT] Fertig. {gefunden} Session(s) gelöscht.")
#         return HttpResponse("OK", status=200)

#     except Exception as e:
#         logger.error(f"[ED-LOGOUT] Fehler beim Verarbeiten: {e}", exc_info=True)
#         return HttpResponse(f"Error processing logout: {str(e)}", status=400)

#nur - Rechentrainer:
def decode_jwt_payload(token):
    """
    Dekodiert NUR den Payload-Teil eines JWT (ohne Signaturprüfung).
    Gibt ein dict zurück, oder None bei Fehlern/leerem Token.
    """
    if not token:
        return None
    try:
        parts = token.split('.')
        if len(parts) < 2:
            return None
        payload_segment = parts[1]
        payload_segment += '=' * (-len(payload_segment) % 4)
        decoded_bytes = base64.urlsafe_b64decode(payload_segment.encode('utf-8'))
        return json.loads(decoded_bytes.decode('utf-8'))
    except Exception:
        return None

def get_oidc_endpoints():
  """Lädt die Discovery-Endpunkte von Eduplaces."""
  try:
    response = requests.get(OIDC_CONFIG_URL, timeout=5)
    if response.status_code == 200:
      data = response.json()
      return data.get("authorization_endpoint"), data.get("token_endpoint"), data.get("userinfo_endpoint")
  except requests.RequestException:
    pass
  return (
      "https://auth.sandbox.eduplaces.dev/oauth/authorize",
      "https://auth.sandbox.eduplaces.dev/oauth/token",
      "https://auth.sandbox.eduplaces.dev/oauth/userinfo",
  )

import secrets
import urllib.parse

import base64
import secrets
import urllib.parse
import re
import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import Group, User
from django.core.mail import send_mail
from django.shortcuts import redirect, render

from .models import LoginLog, Ort, Profil, Schule

def get_oidc_endpoints():
    """Lädt die Discovery-Endpunkte von Eduplaces."""
    try:
        response = requests.get(OIDC_CONFIG_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            return data.get("authorization_endpoint"), data.get("token_endpoint"), data.get("userinfo_endpoint")
    except requests.RequestException:
        pass
    return (
        "https://auth.sandbox.eduplaces.dev/oauth/authorize",
        "https://auth.sandbox.eduplaces.dev/oauth/token",
        "https://auth.sandbox.eduplaces.dev/oauth/userinfo",
    )

def eduplaces_login(request):
    """Leitet den Nutzer zum Eduplaces-Login weiter."""
    auth_endpoint, _, _ = get_oidc_endpoints()
    
    # 1. Sicheren State mit ausreichend Länge generieren und in der Session merken
    state = secrets.token_urlsafe(16)
    request.session['eduplaces_state'] = state
    
    # Scopes um 'profile' für den Klarnamen und 'school_location' ergänzt
    scopes = (
        "openid role pseudony groups school schooling_level school_name"
        " school_location school_official_id"
        " profile"
    )
    
    params = {
        'response_type': 'code',
        'client_id': EDUPLACES_CLIENT_ID,
        'redirect_uri': EDUPLACES_REDIRECT_URI,
        'scope': scopes,
        'state': state,  # Hier wird der State übergeben
    }
    
    redirect_url = f"{auth_endpoint}?{urllib.parse.urlencode(params)}"
    return redirect(redirect_url)

def eduplaces_callback(request):
    """Verarbeitet den Rücksprung von Eduplaces und steuert das Stufen-System."""
    code = request.GET.get("code")
    error = request.GET.get("error")
    if error or not code:
        messages.error(request, "Der Login über Eduplaces wurde abgebrochen oder ist fehlgeschlagen.")
        return redirect("index")
    
    _, token_endpoint, userinfo_endpoint = get_oidc_endpoints()
    
    # 1. Code gegen Token tauschen (mit Basic Auth)
    credentials = f"{EDUPLACES_CLIENT_ID}:{EDUPLACES_CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": EDUPLACES_REDIRECT_URI,
    }

    token_response = requests.post(token_endpoint, data=payload, headers=headers, timeout=10)
    if token_response.status_code != 200:
        messages.error(request, "Fehler beim Token-Austausch mit Eduplaces.")
        return redirect("index")

    token_data = token_response.json()
    access_token = token_data.get("access_token")
    id_token = token_data.get("id_token")
    id_payload = decode_jwt_payload(id_token) or {}
    eduplaces_sid = id_payload.get("sid")

    LoginLog.objects.create(
    quelle='eduplaces_duell_debug',
    consumer_key='ID-TOKEN-PAYLOAD',
    user_id=str(eduplaces_sid),
    user_name='ID Token Payload komplett',
    rolle='',
    institution_name='',
    rohdaten=str(id_payload)
)

    # 2. Benutzerdaten (UserInfo) von Eduplaces abrufen
    userinfo_headers = {"Authorization": f"Bearer {access_token}"}
    userinfo_response = requests.get(userinfo_endpoint, headers=userinfo_headers, timeout=10)
    
    if userinfo_response.status_code != 200:
        messages.error(request, "Fehler beim Abrufen der Benutzerdaten von Eduplaces.")
        return redirect("index")

    ed_data = userinfo_response.json()
    request.session['eduplaces_sub'] = ed_data.get('sub')
    request.session['eduplaces_sid'] = eduplaces_sid
    logger.warning(f"[ED-LOGIN] id_token vorhanden: {id_token is not None}, eduplaces_sid gespeichert: {eduplaces_sid!r}")

    # Daten aus Eduplaces extrahieren
    eduplaces_uid = ed_data.get("sub") or ed_data.get("pseudony")
    vorname = ed_data.get("given_name", "").strip()
    nachname = ed_data.get("family_name", "").strip()
    
    # ROBUSTE ROLLEN-ERKENNUNG
    roh_rolle = str(ed_data.get("role", ed_data.get("rolle", "student"))).lower()
    if any(r in roh_rolle for r in ["lehrer", "teacher", "instructor"]):
        ziel_gruppen_name = "Lehrer"
    else:
        ziel_gruppen_name = "Schüler"

    email = "" 
    
    # Schulinformationen direkt hier definieren, damit sie überall verfügbar sind
    school_name = ed_data.get("school_name", "Unbekannte Schule")
    school_official_id = ed_data.get("school_official_id", None)
    
    raw_location_data = ed_data.get("school_location", "")
    plz_val = None
    
    if isinstance(raw_location_data, dict):
        ort_name_val = raw_location_data.get("state", "Unbekannter Ort")
    else:
        raw_location = str(raw_location_data).strip()
        ort_name_val = raw_location if raw_location else "Unbekannter Ort"
        if raw_location:
            match = re.match(r"^(\d{5})\s+(.*)$", raw_location)
            if match:
                plz_val = match.group(1)
                ort_name_val = match.group(2).strip()
    
    # 3. Ort & Schule in der eigenen Datenbank prüfen / anlegen (PLZ und Name getrennt)
    if plz_val:
        ort_obj, _ = Ort.objects.get_or_create(
            name=ort_name_val,
            defaults={"plz": plz_val}
        )
        if not ort_obj.plz and plz_val:
            ort_obj.plz = plz_val
            ort_obj.save()
    else:
        ort_obj, _ = Ort.objects.get_or_create(
            name=ort_name_val
        )
    
    schule_neu = False
    schule_obj = None
    if school_official_id:
        schule_obj, schule_neu = Schule.objects.get_or_create(
            dienststellen_nr=school_official_id,
            defaults={"schulname": school_name, "ort": ort_obj}
        )
    else:
        schule_obj, schule_neu = Schule.objects.get_or_create(
            schulname=school_name,
            ort=ort_obj
        )

    # LoginLog schreiben
    LoginLog.objects.create(
        quelle='eduplaces',
        consumer_key=school_official_id if school_official_id else 'unbekannt',
        user_id=eduplaces_uid,
        user_name=f"{vorname} {nachname}".strip(),
        rolle=ziel_gruppen_name,
        institution_name=school_name,
        rohdaten=str(ed_data)
    )

    # Wenn es eine ganz neue Schule im System ist, Mail senden
    if schule_neu:
        try:
            send_mail(
                subject="Neue Schule über Eduplaces registriert",
                message=f"Eine neue Schule hat sich über Eduplaces angemeldet:\n\nName: {school_name}\nOrt: {ort_name_val} (PLZ: {plz_val})\nOffizielle ID: {school_official_id}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.ADMINS[0][1] if hasattr(settings, "ADMINS") and settings.ADMINS else "info@rechentrainer.app"],
                fail_silently=True,
            )
        except Exception:
            pass

    # 4. Stufen-Logik

    # STUFE 1: Ist die eduplaces_uid bereits in einem Profil gespeichert?
    try:
        profil = Profil.objects.get(eduplaces_uid=eduplaces_uid)
        user = profil.user
        
        gruppe_obj = Group.objects.filter(name=ziel_gruppen_name).first()
        if gruppe_obj:
            user.groups.add(gruppe_obj)
        if email and user.email != email:
            user.email = email
            user.save()

        login(request, user)
        return redirect("index")
    except Profil.DoesNotExist:
        pass

    # STUFE 2: Keine ID, aber Name & Schule stimmen überein
    if schule_obj:
        profil = Profil.objects.filter(vorname=vorname, nachname=nachname, schule=schule_obj).first()
        if profil:
            user = profil.user
            profil.eduplaces_uid = eduplaces_uid
            profil.save()
            
            gruppe_obj = Group.objects.filter(name=ziel_gruppen_name).first()
            if gruppe_obj:
                user.groups.add(gruppe_obj)
            if email and user.email != email:
                user.email = email
                user.save()
                
            login(request, user)
            return redirect("index")

    # STUFE 3 & 4: Ab in die Session
    request.session["ed_pending"] = {
        "eduplaces_uid": eduplaces_uid,
        "vorname": vorname,
        "nachname": nachname,
        "email": email,
        "rolle": ziel_gruppen_name,
        "schule_id": schule_obj.id if schule_obj else None,
        "jg": 5,
    }

    return redirect("eduplaces_zuordnung")

def eduplaces_zuordnung(request):
    ed_data = request.session.get('ed_pending')
    if not ed_data:
        return redirect('index')

    vorname = ed_data.get('vorname')
    nachname = ed_data.get('nachname')
    
    # HIER IST DER SCHLÜSSEL: Wir holen den festen Wert direkt aus der Session!
    is_lehrer = ed_data.get('is_lehrer', False)
    
    # Falls er noch nicht in der Session war, beim ersten Mal sauber ermitteln und speichern:
    if 'is_lehrer' not in ed_data:
        rohe_rolle = str(ed_data.get('rolle', 'Schüler')).lower()
        is_lehrer = any(r in rohe_rolle for r in ['lehrer', 'teacher', 'instructor'])
        ed_data['is_lehrer'] = is_lehrer
        request.session['ed_pending'] = ed_data

    rolle = 'Lehrer' if is_lehrer else 'Schüler'
    error_message = None
    
    if request.method == 'POST':
        aktion = request.POST.get('aktion')

        if aktion == 'registrierung_speichern':
            if is_lehrer:
                reg_klasse = 'Lehrer'
                reg_jg = 7  # Default-Jahrgang für Lehrer, kann später im Profil geändert werden
            else:
                reg_klasse = request.POST.get('reg_klasse')
                reg_jg = request.POST.get('reg_jg')

            reg_kurs = request.POST.get('reg_kurs')
            reg_email = request.POST.get('reg_email', '').strip()
            ed_uid = ed_data['eduplaces_uid']

            # Holen oder erstellen des aktuellen Schuljahrs und Halbjahrs
            sj, hj = name_hj()
            
            existing_profil = Profil.objects.filter(eduplaces_uid=ed_uid).first()
            if existing_profil:
                new_user = existing_profil.user
                existing_profil.vorname = vorname
                existing_profil.nachname = nachname
                existing_profil.klasse = reg_klasse
                existing_profil.jg = int(reg_jg) if reg_jg else 7
                existing_profil.kurs = reg_kurs
                if ed_data.get('schule_id'):
                    existing_profil.schule_id = ed_data.get('schule_id')
                # Setze die fehlenden Felder, damit die index-Prüfung nicht zu rt_profil_ergaenzen weiterleitet
                existing_profil.mathe = True
                existing_profil.stufe = stufe_aus_jg(int(reg_jg) if reg_jg else 5, reg_kurs)
                existing_profil.sj = sj
                existing_profil.hj = hj
                # Zeitstempel setzen, falls noch leer
                if not existing_profil.schuljahr_ab and not existing_profil.halbjahr_ab:
                    if hj == 1:
                        existing_profil.schuljahr_ab = timezone.now()
                    else:
                        existing_profil.halbjahr_ab = timezone.now()
                existing_profil.save()

                if reg_email and new_user.email != reg_email:
                    new_user.email = reg_email
                    new_user.save()
            else:
                base_username = f'edu_{ed_uid[:10]}'
                username = base_username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f'{base_username}_{counter}'
                    counter += 1

                new_user = User.objects.create_user(
                    username=username,
                    email=reg_email if reg_email else '',
                    password=User.objects.make_random_password(),
                )

                gruppe_obj = Group.objects.filter(name=rolle).first()
                if gruppe_obj:
                    new_user.groups.add(gruppe_obj)

                # Berechne Stufe basierend auf Jahrgang und Kurs
                stufe = stufe_aus_jg(int(reg_jg) if reg_jg else 5, reg_kurs)
                
                Profil.objects.create(
                    user=new_user,
                    vorname=vorname,
                    nachname=nachname,
                    klasse=reg_klasse,
                    jg=int(reg_jg) if reg_jg else 7,
                    kurs=reg_kurs,
                    eduplaces_uid=ed_uid,
                    schule_id=ed_data.get('schule_id'),
                    stufe=stufe,
                    sj=sj,
                    hj=hj,
                    schuljahr_ab=timezone.now() if hj == 1 else None,
                    halbjahr_ab=timezone.now() if hj == 2 else None,
                )

            login(request, new_user)
            
            # Session komplett aufräumen, damit es nie wieder aufgerufen wird
            if 'ed_pending' in request.session:
                del request.session['ed_pending']
            if 'eduplaces_sub' in request.session:
                del request.session['eduplaces_sub']

            return redirect('index')

        elif aktion == 'verknuepfen':
            u_eingabe = request.POST.get('username_eingabe')
            p_eingabe = request.POST.get('passwort_eingabe')

            user = authenticate(request, username=u_eingabe, password=p_eingabe)
            if user is not None:
                profil, _ = Profil.objects.get_or_create(user=user)
                profil.eduplaces_uid = ed_data['eduplaces_uid']
                if ed_data.get('schule_id'):
                    profil.schule_id = ed_data.get('schule_id')
                profil.save()

                gruppe_obj = Group.objects.filter(name=rolle).first()
                if gruppe_obj:
                    user.groups.add(gruppe_obj)

                login(request, user)
                if 'ed_pending' in request.session:
                    del request.session['ed_pending']
                if 'eduplaces_sub' in request.session:
                    del request.session['eduplaces_sub']
                return redirect('index')
            else:
                error_message = 'Benutzername oder Passwort war falsch.'

    context = {
        'moodle_vorname': vorname,
        'moodle_nachname': nachname,
        'moodle_email': ed_data.get('email', ''),
        'form_klasse': 'Lehrer' if is_lehrer else ed_data.get('reg_klasse', ''),
        'form_jg': ed_data.get('jg', 5),
        'kurs_choices': wahl_kurs.choices,
        'error_message': error_message,
        'is_lehrer': is_lehrer,
        'rollen_label': 'Rolle (z.B. Lehrer / Lehrerin):' if is_lehrer else 'Klasse:',
        'rollen_placeholder': 'z.B. Lehrer' if is_lehrer else 'z.B. 6R',
    }

    return render(request, 'SSO/sso_registrierung.html', context)

# nur Duell:
def generate_pkce_pair():
    """Erzeugt ein PKCE code_verifier/code_challenge-Paar (S256)."""
    code_verifier = secrets.token_urlsafe(64)[:128]  # 43-128 Zeichen erlaubt
    challenge_bytes = hashlib.sha256(code_verifier.encode('utf-8')).digest()
    code_challenge = base64.urlsafe_b64encode(challenge_bytes).decode('utf-8').rstrip('=')
    return code_verifier, code_challenge

def eduplaces_login_duell(request):
    """Leitet den Nutzer zum Eduplaces-Login für Rechenduell weiter (mit PKCE)."""
    auth_endpoint, _, _ = get_oidc_endpoints()

    state = secrets.token_urlsafe(16)
    code_verifier, code_challenge = generate_pkce_pair()

    request.session['eduplaces_duell_state'] = state
    request.session['eduplaces_duell_code_verifier'] = code_verifier

    scopes = "openid role pseudonym school school_name school_official_id"

    params = {
        'response_type': 'code',
        'client_id': EDUPLACES_DUELL_CLIENT_ID,
        'redirect_uri': EDUPLACES_DUELL_REDIRECT_URI,
        'scope': scopes,
        'state': state,
        'code_challenge': code_challenge,
        'code_challenge_method': 'S256',
    }

    redirect_url = f"{auth_endpoint}?{urllib.parse.urlencode(params)}"
    return redirect(redirect_url)

def eduplaces_callback_duell(request):
    """Verarbeitet den Rücksprung von Eduplaces für Rechenduell."""
    code = request.GET.get("code")
    error = request.GET.get("error")
    if error or not code:
        messages.error(request, "Der Login über Eduplaces wurde abgebrochen oder ist fehlgeschlagen.")
        return redirect("duell")

    code_verifier = request.session.get('eduplaces_duell_code_verifier')
    if not code_verifier:
        messages.error(request, "Sitzung abgelaufen, bitte erneut versuchen.")
        return redirect("duell")

    _, token_endpoint, userinfo_endpoint = get_oidc_endpoints()

    credentials = f"{EDUPLACES_DUELL_CLIENT_ID}:{EDUPLACES_DUELL_CLIENT_SECRET}"
    encoded_credentials = base64.b64encode(credentials.encode()).decode()
    headers = {
        "Authorization": f"Basic {encoded_credentials}",
        "Content-Type": "application/x-www-form-urlencoded",
    }
    payload = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": EDUPLACES_DUELL_REDIRECT_URI,
        "code_verifier": code_verifier,
    }

    token_response = requests.post(token_endpoint, data=payload, headers=headers, timeout=10)
    if token_response.status_code != 200:
        messages.error(request, "Fehler beim Token-Austausch mit Eduplaces.")
        return redirect("duell")


    token_data = token_response.json()
    access_token = token_data.get("access_token")
    id_token = token_data.get("id_token")
    id_payload = decode_jwt_payload(id_token) or {}
    eduplaces_sid = id_payload.get("sid")

    # DIAGNOSE: kompletten Token-Response anschauen
    LoginLog.objects.create(
        quelle='eduplaces_duell_debug',
        consumer_key='TOKEN-DATA',
        user_id='',
        user_name='Token Data + ID Payload',
        rolle='',
        institution_name='',
        rohdaten=f"token_data keys: {list(token_data.keys())} | id_payload: {id_payload}"
    )

    userinfo_headers = {"Authorization": f"Bearer {access_token}"}
    userinfo_response = requests.get(userinfo_endpoint, headers=userinfo_headers, timeout=10)

    if userinfo_response.status_code != 200:
        messages.error(request, "Fehler beim Abrufen der Benutzerdaten von Eduplaces.")
        return redirect("duell")

    ed_data = userinfo_response.json()
    request.session['eduplaces_sub'] = ed_data.get('sub')
    request.session['eduplaces_sid'] = eduplaces_sid

    # Daten aus Eduplaces extrahieren (identisch zum Rechentrainer)
    eduplaces_uid = ed_data.get("sub") or ed_data.get("pseudonym")
    vorname = ed_data.get("given_name", "").strip()
    nachname = ed_data.get("family_name", "").strip()

    roh_rolle = str(ed_data.get("role", ed_data.get("rolle", "student"))).lower()
    if any(r in roh_rolle for r in ["lehrer", "teacher", "instructor"]):
        ziel_gruppen_name = "Lehrer"
    else:
        ziel_gruppen_name = "Schüler"

    email = ""

    school_name = ed_data.get("school_name", "Unbekannte Schule")
    school_official_id = ed_data.get("school_official_id", None)

    raw_location_data = ed_data.get("school_location", "")
    plz_val = None

    if isinstance(raw_location_data, dict):
        ort_name_val = raw_location_data.get("state", "Unbekannter Ort")
    else:
        raw_location = str(raw_location_data).strip()
        ort_name_val = raw_location if raw_location else "Unbekannter Ort"
        if raw_location:
            match = re.match(r"^(\d{5})\s+(.*)$", raw_location)
            if match:
                plz_val = match.group(1)
                ort_name_val = match.group(2).strip()

    if plz_val:
        ort_obj, _ = Ort.objects.get_or_create(
            name=ort_name_val,
            defaults={"plz": plz_val}
        )
        if not ort_obj.plz and plz_val:
            ort_obj.plz = plz_val
            ort_obj.save()
    else:
        ort_obj, _ = Ort.objects.get_or_create(name=ort_name_val)

    schule_neu = False
    schule_obj = None
    if school_official_id:
        schule_obj, schule_neu = Schule.objects.get_or_create(
            dienststellen_nr=school_official_id,
            defaults={"schulname": school_name, "ort": ort_obj}
        )
    else:
        schule_obj, schule_neu = Schule.objects.get_or_create(
            schulname=school_name,
            ort=ort_obj
        )

    LoginLog.objects.create(
        quelle='eduplaces_duell',
        consumer_key=school_official_id if school_official_id else 'unbekannt',
        user_id=eduplaces_uid,
        user_name=f"{vorname} {nachname}".strip(),
        rolle=ziel_gruppen_name,
        institution_name=school_name,
        rohdaten=str(ed_data)
    )

    # STUFE 1: eduplaces_uid bereits bekannt -> einloggen
    try:
        profil = Profil.objects.get(eduplaces_uid=eduplaces_uid)
        user = profil.user
        gruppe_obj = Group.objects.filter(name=ziel_gruppen_name).first()
        if gruppe_obj:
            user.groups.add(gruppe_obj)
        if email and user.email != email:
            user.email = email
            user.save()
        login(request, user)
        return redirect("duell")
    except Profil.DoesNotExist:
        pass

    # STUFE 2: Name + Schule stimmen überein -> verknüpfen
    if schule_obj:
        profil = Profil.objects.filter(vorname=vorname, nachname=nachname, schule=schule_obj).first()
        if profil:
            user = profil.user
            profil.eduplaces_uid = eduplaces_uid
            profil.save()
            gruppe_obj = Group.objects.filter(name=ziel_gruppen_name).first()
            if gruppe_obj:
                user.groups.add(gruppe_obj)
            if email and user.email != email:
                user.email = email
                user.save()
            login(request, user)
            return redirect("duell")

    # STUFE 3: Komplett neu -> DIREKT anlegen, KEIN Formular, KEIN jg/kurs
    sj, hj = name_hj()
    base_username = f'edu_duell_{eduplaces_uid[:10]}'
    username = base_username
    counter = 1
    while User.objects.filter(username=username).exists():
        username = f'{base_username}_{counter}'
        counter += 1

    new_user = User.objects.create_user(
        username=username,
        password=User.objects.make_random_password(),
    )

    gruppe_obj = Group.objects.filter(name=ziel_gruppen_name).first()
    if gruppe_obj:
        new_user.groups.add(gruppe_obj)

    Profil.objects.create(
        user=new_user,
        vorname=vorname,
        nachname=nachname,
        klasse='',
        schule=schule_obj,
        eduplaces_uid=eduplaces_uid,
        mathe=False,
        sj=sj,
        hj=hj,
    )

    login(request, new_user)
    return redirect("duell")

@csrf_exempt
def simulation_eduplaces(request):
  if request.method == 'POST':
    # Wir füttern die Session direkt mit den Simulationsdaten,
    # genau so, wie sie normalerweise von Eduplaces kommen würden.
    request.session['ed_pending'] = {
        'eduplaces_uid': request.POST.get('uid', 'sim_user_123'),
        'vorname': request.POST.get('vorname', 'Max'),
        'nachname': request.POST.get('nachname', 'Mustermann'),
        'rolle': request.POST.get('rolle', 'student'),
        'schule_id': None,  # Wird über die offizielle ID verknüpft
    }

    # Wir simulieren direkt die Daten, die sonst aus dem Userinfo-Endpoint kämen,
    # und legen Ort & Schule direkt an:
    school_name = request.POST.get('schulname', 'IGS Kelsterbach')
    school_location = request.POST.get('ort', 'Kelsterbach')
    school_official_id = request.POST.get('school_official_id', 'D_HE_6072')

    ort_obj, _ = Ort.objects.get_or_create(name=school_location)
    schule_obj, _ = Schule.objects.get_or_create(
        dienststellen_nr=school_official_id,
        defaults={'schulname': school_name, 'ort': ort_obj}
    )

    # Aktualisiere die Session mit der echten Schul-ID
    pending = request.session['ed_pending']
    pending['schule_id'] = schule_obj.id
    request.session['ed_pending'] = pending

    # Stufe 1 Prüfung direkt hier oder Weiterleitung zur Zuordnung:
    # Versuche direkt, ob ein Profil mit dieser UID existiert
    try:
      profil = Profil.objects.get(eduplaces_uid=pending['eduplaces_uid'])
      login(request, profil.user)
      messages.success(request, f'Simulation: Erfolgreich eingeloggt als {profil.vorname}!')
      return redirect('index')
    except Profil.DoesNotExist:
      pass

    # Wenn kein Profil da ist, leiten wir zur Zuordnungsmaske weiter (Stufe 2-4)
    return redirect('eduplaces_zuordnung')

  # HTML-Formular für die Eduplaces-Simulation
  return HttpResponse("""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Eduplaces-Login-Simulation</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; }
                form { background: #f0f8ff; padding: 20px; border-radius: 8px; border: 1px solid #b0c4de; }
                input, select, button { padding: 8px; margin: 5px 0; width: 100%; box-sizing: border-box; }
                button { background: #007bff; color: white; border: none; cursor: pointer; }
            </style>
        </head>
        <body>
            <h1>Eduplaces-Login-Simulation</h1>
            <p>Simuliert den Rücksprung und die Datenübergabe von der Eduplaces-Sandbox.</p>
            <form method="POST">
                <label>Eduplaces UID / Pseudonym:</label>
                <input type="text" name="uid" value="edu_test_lehrer1"><br>

                <label>Vorname:</label>
                <input type="text" name="vorname" value="Anna"><br>

                <label>Nachname:</label>
                <input type="text" name="nachname" value="Lehrerin"><br>

                <label>Rolle:</label>
                <select name="rolle">
                    <option value="teacher">Lehrkraft (teacher)</option>
                    <option value="student">Schüler (student)</option>
                </select><br>

                <label>Schulname:</label>
                <input type="text" name="schulname" value="IGS Kelsterbach"><br>

                <label>Ort:</label>
                <input type="text" name="ort" value="Kelsterbach"><br>

                <label>Offizielle Schul-ID (dienststellen_nr):</label>
                <input type="text" name="school_official_id" value="D_HE_6072"><br>

                <button type="submit">Eduplaces-Login simulieren</button>
            </form>
        </body>
        </html>
    """)

def account_loeschen(req):
    try:    
        user = User.objects.get(pk = req.user.id)
    except:
        messages.error(req, "Es ist kein Benutzer angemeldet!!")        
        return render(req, 'mathe_start.html')        
    if req.method == 'POST':
        bestaetigt = req.POST.get('bestaetigt', 'off')        
        if bestaetigt == "on":
            logout(req)
            user.delete()
            messages.success(req, "Dein Account und alle deine Daten wurden gelöscht!")
        else:
            messages.error(req, "Löschen wurde abgebrochen!")
        return render(req, 'mathe_start.html')
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
    sj, hj = name_hj() # Stellt sicher, dass diese Funktion in deinem Scope existiert
    
    # 1. Schülerauswertung
    alleschueler = []
    schueler = Profil.objects.select_related('gruppe__lehrer__profil').all()
    for s in schueler:
        startdatum = s.gruppe.erstellt_am if s.gruppe else s.user.date_joined
        schulwoche, woche_halbjahr, soll_hj, soll_kat, pflicht_kat = soll_berechnung(sj, hj, s.jg, s.jg*10, startdatum) 
        
        protokolle = Protokoll.objects.filter(profil=s)
        hjsumme_val = protokolle.filter(sj=sj, hj=hj).aggregate(sum=Sum('richtig'))['sum']
        hjsumme = int(hjsumme_val) if isinstance(hjsumme_val, Decimal) else (hjsumme_val or 0)

        if hjsumme > soll_hj: # Nur die Aktiven
            alleschueler.append({
                "initialen": f"{s.vorname[0]}. {s.nachname[0]}.",
                "hjsumme": hjsumme,
                "gruppe": s.gruppe.name if s.gruppe else "n.a.",
                "schule": s.gruppe.lehrer.profil.schule.schulname if (s.gruppe and s.gruppe.lehrer) else "n.a."
            })
    
    hjschueler = sorted(alleschueler, key=lambda x: x["hjsumme"], reverse=True)[:10]

    # 2. Gruppenauswertung (Aktuelles Halbjahr)
    hjgruppen = []
    for g in Lerngruppe.objects.all():
        schulwoche, woche_halbjahr, soll_hj, soll_kat, pflicht_kat = soll_berechnung(sj, hj, g.jg, g.jg*10, g.erstellt_am) 
        mitglieder = Profil.objects.filter(gruppe=g).count()
        
        if mitglieder > 0:
            protokoll_hj = Protokoll.objects.filter(profil__gruppe=g, sj=sj, hj=hj)
            hjsumme_val = protokoll_hj.aggregate(sum=Sum('richtig'))['sum']
            hjsumme = int(hjsumme_val) if isinstance(hjsumme_val, Decimal) else (hjsumme_val or 0)

            if hjsumme > (mitglieder * soll_hj * 0.5):
                hjgruppen.append({
                    "gruppe": g, 
                    "mitglieder": mitglieder,
                    "hjsumme": hjsumme, 
                    "hjschnitt": round(hjsumme / mitglieder)
                })

    hjgruppen = sorted(hjgruppen, key=lambda x: x["hjsumme"], reverse=True)[:10]

    context = {
        'hjliste': hjschueler, 
        'ewigeliste': EwigeBestenliste.objects.all().order_by('-punkte')[:10],
        'hjgruppen': hjgruppen
    }
    return render(req, 'bestenliste.html', context)

def statistik(req):
    kategorien = Kategorie.objects.all().order_by('zeile')
    kategorienliste = []
    max_count = 0
    
    # 1. JSON-Zähler einlesen
    json_pfad = Path(settings.BASE_DIR) / "core" / "zaehler_geloeschte_aufgaben.json"
    json_wert = 0
    if json_pfad.exists():
        try:
            with open(json_pfad, 'r', encoding='utf-8') as f:
                json_daten = json.load(f)
                json_wert = json_daten.get('anzahl', 0)
        except:
            json_wert = 0
            
    # 2. Datenbank-Daten sammeln
    gesamt_protokolle = Protokoll.objects.count()
    gesamt_geloescht_in_kategorien = sum(k.geloeschte_aufgaben for k in kategorien)
    
    # 3. Gesamtsumme = JSON-Altbestand + Kategorie-Gelöschte + Aktuelle Protokolle
    gesamt = json_wert + gesamt_protokolle + gesamt_geloescht_in_kategorien
    
    for kategorie in kategorien:
        aktuelle_anzahl = Protokoll.objects.filter(kategorie=kategorie).count()
        # Hinweis: Hier nutzen wir nur die datenbankseitigen gelöschten Aufgaben, 
        # da wir den JSON-Wert nicht auf einzelne Kategorien runterbrechen können.
        summe_mit_geloeschten = aktuelle_anzahl + kategorie.geloeschte_aufgaben
        
        kategorienliste.append([kategorie, summe_mit_geloeschten])
        
        if summe_mit_geloeschten > max_count:
            max_count = summe_mit_geloeschten
            
    # Prozentuale Breite berechnen
    if max_count > 0:
        for eintrag in kategorienliste:
            prozent = (eintrag[1] / max_count) * 100
            eintrag.append(f"width:{round(prozent, 1)}%")
    else:
        for eintrag in kategorienliste:
            eintrag.append("width:0%")
            
    return render(req, 'statistik.html', context={'gesamt': gesamt, 'kategorien': kategorienliste})

def alle_lehrer(req):
    if not req.user.is_superuser:
        return HttpResponse("Zugriff verweigert")

    lerngruppen_qs = Lerngruppe.objects.annotate(
        schueler_anzahl=Count('profile')
    ).order_by('name')

    lehrer_qs = (
        User.objects.filter(groups__name="Lehrer")
        .select_related('profil__schule__ort')
        .prefetch_related(Prefetch('lerngruppen', queryset=lerngruppen_qs))
        .distinct()
        .order_by(
            'profil__schule__ort__plz',
            'profil__schule__ort__name',
            'profil__schule__schulname',
            'profil__nachname',
            'profil__vorname',
        )
    )

    def schul_key(u):
        schule = u.profil.schule
        if schule:
            ort = schule.ort
            plz = ort.plz if ort else ""
            ort_name = ort.name if ort else ""
            return (plz, ort_name, schule.schulname)
        return ("", "", "")

    schulen = []
    for (plz, ort_name, schulname), gruppe in groupby(lehrer_qs, key=schul_key):
        schulen.append({
            'plz': plz or None,
            'ort': ort_name or None,
            'schule': schulname or None,
            'lehrer': list(gruppe),
        })

    return render(
        req,
        'admin/alle_lehrer.html',
        context={'schulen': schulen, 'titel': "Lehrerübersicht"},
    )

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
        # Prüfen, ob der Benutzer in der Gruppe "Lehrer" ist
        if req.user.groups.filter(name="Lehrer").exists():
            # Lehrer: Prüfen, ob Schule einen Ort hat
            hat_ort = schule.ort is not None
            return render(req, 'lehrer/wahl_fertig.html', {
                'schule': schule,
                'titel': "fertig",
                'ist_lehrer': True,
                'hat_ort': hat_ort
            })
        else:
            # Kein Lehrer: Mail-Meldung
            return render(req, 'lehrer/wahl_fertig.html', {
                'schule': schule,
                'titel': "fertig",
                'ist_lehrer': False,
                'hat_ort': schule.ort is not None
            })
    else:
        return render(req, 'schueler/lehrer_wahl.html', context={'lehrer_liste': lehrer_liste, 'schule': schule, 'titel': "Lehrer/in wählen"}) 

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