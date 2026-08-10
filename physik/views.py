import random

from dotenv import load_dotenv

from django.http import HttpResponse, JsonResponse

from django.contrib import messages
from django.contrib.messages import get_messages
from django.views.decorators.csrf import csrf_exempt

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test

from django.shortcuts import render, redirect, get_object_or_404

from django.db.models import Count, Q

from accounts.models import Profil
from accounts.forms import  Login_Form, Suchen_Form, Loeschen_Form, Zusammen_Form, Abmelden_Form

from .models import ThemenBereich, Kapitel, Aufgabe, FehlerLog, AufgabeOption, Protokoll
from .forms import Register_Form, Profil_Form

from .bewertung import bewerte_aufgabe, check_answer_with_api

def ist_mitarbeiter(user):
    if not user.is_authenticated:
        return False
    return user.groups.filter(name='Mitarbeiter').exists()

def berechne_sperre(total, f1_bestand, f2_bestand, ziel_fach, f3_bestand=0):
    ready = True
    hint = ""
    
    if ziel_fach == 2:
        bestand = f2_bestand
        if bestand > 0 and total > 0:
            erledigt = total - f1_bestand
            if (erledigt / total) < 0.75:
                ready = False
                hint = f"Noch {int(0.75 * total - erledigt) + 1} in Fach 1 lösen."
        return bestand, ready, hint
        
    if ziel_fach == 3:
        bestand = f3_bestand
        if bestand > 0 and total > 0:
            erledigt = total - f1_bestand - f2_bestand
            if (erledigt / total) < 0.75:
                ready = False
                hint = f"Noch {int(0.75 * total - erledigt) + 1} in Fach 2 lösen."
        return bestand, ready, hint

def index(request):
    # Reset Session
    for k in ("aufgaben_ids", "index", "p_richtig", "letzte_antwort", "warte_auf_weiter"):
        request.session.pop(k, None)
    themenbereiche = ThemenBereich.objects.filter(eingeblendet=True).prefetch_related("kapitel").order_by("ordnung")
    # 1. Die kapitel_map für das JavaScript-Modal
    kapitel_map = {
            str(tb.id): [{"zeile": k.zeile, "name": k.kapitel} for k in tb.kapitel.all().order_by("zeile")]
            for tb in themenbereiche
        }
    # 2. Alle Aufgaben zählen (Gesamtbestand)
    qs_gesamt = (
        Aufgabe.objects.filter(thema__in=themenbereiche)
        .values("thema_id", "kapitel_id", "schwierigkeit")
        .annotate(cnt=Count("id"))
    )
    # 3. Lernstand des Users abrufen (nur wenn eingeloggt)
    user_protokoll = {}
    profil = None
    if request.user.is_authenticated:
        profil, created = Profil.objects.get_or_create(user=request.user)
        # Beta-Hinweis für Mathe-Nutzer, die zum ersten Mal Physik nutzen
        if not profil.physik:
            profil.physik = True
            profil.save()
            return redirect('physik:beta_hinweis')
        qp = (
            Protokoll.objects.filter(user=request.user, aufgabe__thema__in=themenbereiche)
            .values("aufgabe__thema_id", "aufgabe__kapitel_id", "aufgabe__schwierigkeit", "fach")
            .annotate(cnt=Count("id"))
        )
        for r in qp:
            t_id = r["aufgabe__thema_id"]
            k_id = r["aufgabe__kapitel_id"]
            s = str(r["aufgabe__schwierigkeit"])
            f = r["fach"]
            user_protokoll.setdefault(t_id, {}).setdefault(k_id, {}).setdefault(s, {})
            user_protokoll[t_id][k_id][s][f] = r["cnt"]
    # 4. Counts-Dict aufbauen
    counts = {}
    for r in qs_gesamt:
        t_id = r["thema_id"]
        k_id = r["kapitel_id"]
        s = str(r["schwierigkeit"])
        gesamt = r["cnt"]

        p_data = user_protokoll.get(t_id, {}).get(k_id, {}).get(s, {})
        f2 = p_data.get(2, 0) # Fach 1 (in deiner Logik '2')
        f3 = p_data.get(3, 0) # Fach 2 (in deiner Logik '3')
        f4 = p_data.get(4, 0) # Fach 3 / Archiv (in deiner Logik '4')

        f0 = gesamt - (f2 + f3 + f4)

        counts.setdefault(t_id, {}).setdefault(k_id, {})
        counts[t_id][k_id][s] = {
            '0': f0, '1': f2, '2': f3, '3': f4, 'total': gesamt
        }
    # 5. tb_totals berechnen (Summen für die Kopfzeile)
    tb_totals = {}
    for tb in themenbereiche:
        t_stats = {
            "s1": {"0":0, "1":0, "2":0, "3":0, "total":0},
            "s2": {"0":0, "1":0, "2":0, "3":0, "total":0},
            "s3": {"0":0, "1":0, "2":0, "3":0, "total":0},
            "sum_em": 0, "sum_all": 0
        }
        
        # Reset kum_stats für die Sperr-Logik
        kum_stats = {
            "1": {"total": 0, "f1": 0, "f2": 0, "f3": 0},
            "2": {"total": 0, "f1": 0, "f2": 0, "f3": 0},
            "3": {"total": 0, "f1": 0, "f2": 0, "f3": 0},
        }

        for kap in tb.kapitel.all().order_by("zeile"):
            if tb.id not in counts: counts[tb.id] = {}
            if kap.id not in counts[tb.id]: counts[tb.id][kap.id] = {}
            
            for lvl in ["1", "2", "3"]:
                if lvl not in counts[tb.id][kap.id]:
                    counts[tb.id][kap.id][lvl] = {'0':0, '1':0, '2':0, '3':0, 'total':0}
                
                c_raw = counts[tb.id][kap.id][lvl]
                s_key = f"s{lvl}"
                
                # Summen für Kopfzeile (tb_totals)
                for f_key in ['0', '1', '2', '3', 'total']:
                    t_stats[s_key][f_key] += c_raw.get(f_key, 0)

                # Kumulieren für Sperr-Logik
                kum_stats[lvl]["total"] += c_raw.get('total', 0)
                kum_stats[lvl]["f1"]    += c_raw.get('0', 0)
                kum_stats[lvl]["f2"]    += c_raw.get('1', 0)
                kum_stats[lvl]["f3"]    += c_raw.get('2', 0)

            # --- HIER DEINE SPERR-LOGIK (t1, t2, t3, berechne_sperre) UNVERÄNDERT LASSEN ---
            t1 = kum_stats["1"]["total"]
            f1_1 = kum_stats["1"]["f1"]; f2_1 = kum_stats["1"]["f2"]; f3_1 = kum_stats["1"]["f3"]
            
            t2 = t1 + kum_stats["2"]["total"]
            f1_2 = f1_1 + kum_stats["2"]["f1"]; f2_2 = f2_1 + kum_stats["2"]["f2"]; f3_2 = f3_1 + kum_stats["2"]["f3"]
            
            t3 = t2 + kum_stats["3"]["total"]
            f1_3 = f1_2 + kum_stats["3"]["f1"]; f2_3 = f2_2 + kum_stats["3"]["f2"]; f3_3 = f3_2 + kum_stats["3"]["f3"]

            counts[tb.id][kap.id]["1"]["kum_f2"], counts[tb.id][kap.id]["1"]["f2_ready"], _ = berechne_sperre(t1, f1_1, f2_1, 2)
            # ... (Rest deiner berechne_sperre Aufrufe hier einfügen)

        # Quersummen Kopfzeile
        t_stats["sum_em"] = t_stats["s1"]["total"] + t_stats["s2"]["total"]
        t_stats["sum_all"] = t_stats["sum_em"] + t_stats["s3"]["total"]
        tb_totals[tb.id] = t_stats
    return render(request, "physik/physik_start.html", {
            "themenbereiche": themenbereiche,
            "counts": counts,
            "tb_totals": tb_totals, # <--- WICHTIG: Muss in den Context!
            "kapitel_map": kapitel_map,
            'profil': profil,
            "ist_mitarbeiter": ist_mitarbeiter(request.user),
        })

def anmelden(req):
    titel = "Anmelden" 
    if req.method == 'POST':
        #get_expire_at_browser_close()
        form = Login_Form(req.POST)
        if  form.is_valid ():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']            
            user = authenticate(req, username=username, password=password)

            if user is not None:
                login(req, user)

                return redirect('physik:index')

        titel = "Username und/oder Passwort stimmen nicht"
    form = Login_Form()
    context = {'form' : form, 'titel': titel} 
    return render(req, 'physik/anmelden.html', context)

def beta_hinweis(request):
    if request.method == 'POST':
        aktion = request.POST.get('aktion')
        if aktion == 'ok':
            # Prüfen, ob der Nutzer schon eingeloggt ist (kam über index / Mathe-Wechsel)
            if request.user.is_authenticated:
                return redirect('physik:index')
            else:
                # Kam über die Registrierung -> weiter zum Formular
                request.session['beta_akzeptiert'] = True
                return redirect('physik:registrieren')
        else:
            # Bei Abbrechen immer zurück zur Hauptseite / Index
            if 'beta_akzeptiert' in request.session:
                del request.session['beta_akzeptiert']
            return redirect('index') # oder 'physik:index', je nachdem wohin der Abbruch führen soll
            
    return render(request if 'req' in locals() else request, 'physik/beta_hinweis.html')

def registrieren(req):
    # Schutz: Wenn der Beta-Hinweis noch nicht bestätigt wurde, dorthin umleiten
    if not req.session.get('beta_akzeptiert'):
        return redirect('physik:beta_hinweis')

    reg_form = Register_Form()
    profil_form = Profil_Form()  
    datenschutz = ""
    if req.method == 'POST':
        datenschutz = req.POST.get('datenschutz', 'off')
        reg_form = Register_Form(req.POST)
        profil_form = Profil_Form(req.POST)  
        if datenschutz == "on":
            if reg_form.is_valid() and profil_form.is_valid(): 
                user = reg_form.save()
                profil = profil_form.save(commit=False)
                profil.user = user
                profil.physik = True
                profil.save()
                # Direkt einloggen
                username = reg_form.cleaned_data['username']
                password = reg_form.cleaned_data['password1']
                user = authenticate(username=username, password=password)
                login(req, user)
                
                # Session-Flag für Beta wieder aufräumen
                if 'beta_akzeptiert' in req.session:
                    del req.session['beta_akzeptiert']
                    
                if req.POST.get('cookie_loeschen') == 'on':
                    req.session.set_expiry(0)
                return redirect('physik:index')

    context = {
        'reg_form': reg_form, 
        'profil_form': profil_form, 
        'datenschutz': datenschutz,
        'titel': "Registrieren"
    } 
    return render(req, 'physik/registrieren.html', context)

def force_logout(request):
    logout(request)
    return redirect('physik:index')

@login_required(login_url='/physik/anmelden/')
def update_view_settings(request, slug):
    try:
        # Sicherer Weg: Profil über das Model suchen
        profil, created = Profil.objects.get_or_create(user=request.user)
        
        # Feldname: Physik_einstellungen
        einstellungen = profil.physik_einstellungen if isinstance(profil.physik_einstellungen, dict) else {}
        
        versteckt = list(einstellungen.get("versteckt", []))
        
        if slug in versteckt:
            versteckt.remove(slug)
        else:
            versteckt.append(slug)
            if slug == "mittel" and "profi" not in versteckt:
                versteckt.append("profi")
        
        einstellungen["versteckt"] = versteckt
        profil.physik_einstellungen = einstellungen
        profil.save()
        
        return JsonResponse({"status": "ok", "versteckt": versteckt})
    except Exception as e:
        return JsonResponse({"status": "error", "message": str(e)}, status=500)

@login_required(login_url='/physik/anmelden/')    
def update_row_settings(request, slug):
    profil, created = Profil.objects.get_or_create(user=request.user)
    einstellungen = profil.physik_einstellungen if isinstance(profil.physik_einstellungen, dict) else {}
    
    if 'zeilen_versteckt' not in einstellungen:
        einstellungen['zeilen_versteckt'] = []
    
    if slug in einstellungen['zeilen_versteckt']:
        einstellungen['zeilen_versteckt'].remove(slug)
    else:
        einstellungen['zeilen_versteckt'].append(slug)
    
    profil.physik_einstellungen = einstellungen
    profil.save()
    
    return JsonResponse({'status': 'ok', 'versteckt': einstellungen['zeilen_versteckt']})
    
@login_required(login_url='/physik/anmelden/')
def aufgaben(request):
    anmerkung_fuer_template = ""
    
    # NEU: Wenn 'tb' in der URL steht, wollen wir IMMER eine neue Serie starten,
    # auch wenn 'aufgaben_ids' schon in der Session existieren.
    if request.GET.get("tb"):
        # 0. Vorbereitung: Alte Session & Messages aufräumen
        for k in ("aufgaben_ids", "index", "p_richtig", "letzte_antwort", "warte_auf_weiter"):
            request.session.pop(k, None)
        
        storage = get_messages(request)
        for message in storage: pass

        # 1. Parameter aus GET holen
        tb_id = request.GET.get("tb")
        level_param = request.GET.get("level", "3") # Standard 3
        bis_kap_zeile = request.GET.get("bis_kap")
        
        # Diese bleiben für das Overlay wichtig:
        start_kap = int(request.GET.get("start", 0))
        end_kap = int(request.GET.get("end", 999))
        fach_int = int(request.GET.get("fach", 1))

        # 2. Grundfilterung
        thema = ThemenBereich.objects.get(id=tb_id)
        aufgaben_qs = Aufgabe.objects.filter(thema=thema)

        # --- NEU: Kapitel-Logik unterscheiden ---
        
        # Fall A: Das Thema ist als "kapitel_unabhaengig" markiert (z.B. Sonstige)
        if thema.kapitel_unabhaengig:
            if bis_kap_zeile:
                # Nur EXAKT dieses Kapitel (keine kumulative Summe)
                aufgaben_qs = aufgaben_qs.filter(kapitel__zeile=int(bis_kap_zeile))
            else:
                # Bereich bleibt wie gewählt (meist nur ein Kapitel im Overlay)
                aufgaben_qs = aufgaben_qs.filter(
                    kapitel__zeile__gte=start_kap,
                    kapitel__zeile__lte=end_kap
                )
        
        # Fall B: Normales Verhalten (Physik-Themen: Aufbauend/Kumulativ)
        else:
            if bis_kap_zeile:
                # Weg über die Index-Tabelle (kumulativ: alle bis hierhin)
                aufgaben_qs = aufgaben_qs.filter(kapitel__zeile__lte=int(bis_kap_zeile))
            else:
                # Klassischer Weg über das Overlay (Bereich)
                aufgaben_qs = aufgaben_qs.filter(
                    kapitel__zeile__gte=start_kap,
                    kapitel__zeile__lte=end_kap
                )

        # --- NEU: Level-Logik (kumuliert für 1,2 etc.) ---
        if isinstance(level_param, str) and "," in level_param:
            levels = [int(l) for l in level_param.split(",")]
            aufgaben_qs = aufgaben_qs.filter(schwierigkeit__in=levels)
        else:
            aufgaben_qs = aufgaben_qs.filter(schwierigkeit__lte=int(level_param))

        # 3. Spezifische Fach-Filterung (DEIN BESTEHENDER CODE)
        if fach_int == 1: 
            aufgaben_qs = aufgaben_qs.filter(
                Q(protokoll__user=request.user, protokoll__fach=1) | 
                ~Q(protokoll__user=request.user)
            ).distinct()
        else:
            aufgaben_qs = aufgaben_qs.filter(
                protokoll__user=request.user, 
                protokoll__fach=fach_int
            )

        # 3. Spezifische Fach-Filterung
        # fach_int kommt oben aus request.GET.get("fach")
        if fach_int == 1: 
            # Zeigt nur Aufgaben, die noch "neu" sind oder explizit in Fach 1 liegen
            aufgaben_qs = aufgaben_qs.filter(
                Q(protokoll__user=request.user, protokoll__fach=1) | 
                ~Q(protokoll__user=request.user)
            ).distinct()
        else:
            # Filtert exakt auf Fach 2, 3 oder 4
            aufgaben_qs = aufgaben_qs.filter(
                protokoll__user=request.user, 
                protokoll__fach=fach_int
            )
            
        # 4. IDs extrahieren & initialisieren
        all_ids = list(aufgaben_qs.values_list("id", flat=True))
        
        if not all_ids:
            messages.info(request, f"Keine Aufgaben in diesem Bereich gefunden.")
            return redirect('physik:index')

        random.shuffle(all_ids)
        request.session["aufgaben_ids"] = all_ids[:10]
        request.session["index"] = 0
        request.session["warte_auf_weiter"] = False
        
        # WICHTIG: Redirect auf die URL ohne Parameter, damit ein Refresh 
        # nicht die Serie neu startet
        return redirect("physik:aufgaben")
    
    # 7. Aktuellen Stand aus der Session holen
    ids_in_session = request.session.get("aufgaben_ids", [])
    index = request.session.get("index", 0)

    # 8. Check: Serie beendet?
    if index >= len(ids_in_session):
        for k in ("aufgaben_ids", "index", "p_richtig", "letzte_antwort", "warte_auf_weiter"):
            request.session.pop(k, None)
        return redirect("physik:index")

    # 9. Aktuelle Aufgabe laden
    aufgabe = Aufgabe.objects.get(id=ids_in_session[index])
    
# -------- Medien (Bilder & Videos) --------
    bilder_anzeige = None
    
    # Wir holen die Bilder/Videos immer, wenn welche da sind
    bilder = list(aufgabe.bilder.order_by("position"))
    
    if bilder:
        # ---- Fall 1: Echte Bildfrage (Typ enthält 'p') ----
        if "p" in aufgabe.typ:
            # Nur bei Typ genau 'p' setzen wir die richtige Bild-Antwort
            if aufgabe.typ == "p":
                p_richtig = bilder[0].id
                request.session["p_richtig"] = p_richtig
            
            # Bilder mischen, damit das richtige nicht immer an Platz 1 steht
            random.shuffle(bilder)
        
        # ---- Fall 2: Illustration / Video (z.B. Typ 'a' oder 'va') ----
        else:
            request.session.pop("p_richtig", None)
            # Bei Videos oder normalen Illustrationen NICHT mischen? 
            # Meistens will man Videos an Position 1 behalten.
            pass 

        bilder_anzeige = bilder

    optionen_liste = []
    anzeigen = []
    if "r" in aufgabe.typ:
        # 1. Optionen nach Position sortiert holen
        optionen = aufgabe.optionen.all().order_by('position')
        
        if optionen.exists():
            # 2. Anzahl der Werte aus der ersten Option ermitteln
            # Wir splitten den Text und zählen die Elemente
            erstes_opt_text = optionen[0].text
            anzahl_werte = len(erstes_opt_text.split(';'))

            # 3. Zufallsindex bestimmen
            # Wir versuchen den Index aus der Session zu holen, damit er stabil bleibt
            idx = request.session.get('aktiver_index')
            
            # Falls kein Index da ist oder er nicht mehr zu den Daten passt, neu würfeln
            if idx is None or idx >= anzahl_werte:
                idx = random.randrange(anzahl_werte)
                request.session['aktiver_index'] = idx

            # 4. Die Werte-Liste für .format() zusammenstellen
            # Wir nehmen von jeder Option den Wert an der Stelle 'idx'
            auswahl_liste = []
            for opt in optionen:
                werte = [v.strip() for v in opt.text.split(';')]
                if idx < len(werte):
                    auswahl_liste.append(werte[idx])
                else:
                    # Fallback, falls eine Liste mal kürzer ist
                    auswahl_liste.append("???")

            # 5. Fragetext formatieren
            # Hier werden {0}, {1}, {2} etc. durch die Liste ersetzt
            try:
                # Wichtig: Der Stern * entpackt die Liste für die Positions-Platzhalter
                aufgabe.frage = aufgabe.frage.format(*auswahl_liste)
            except (IndexError, TypeError):
                # Falls die Anzahl der {} im Text nicht zur Anzahl der Optionen passt
                pass

    if "a" in aufgabe.typ:
        # Wir bauen eine Liste aus (Index, Text) Paaren
        optionen_liste = [(0, aufgabe.loesung)] # Index 0 ist immer die richtige Antwort
        for i, o in enumerate(aufgabe.optionen.order_by("position"), start=1):
            optionen_liste.append((i, o.text))
        random.shuffle(optionen_liste)

    # Spezialfall: Überschreibe für Typ 'e'
    elif "e" in (aufgabe.typ or "").lower():
        anmerkung_fuer_template = "Bitte beide Begriffe mit ';' oder '...' trennen."

# -------- POST --------
    if request.method == "POST":
        antwort = request.POST.get("user_antwort") or request.POST.get("antwort", "")
        bild_antwort = request.POST.get("bild_antwort")

        # ---- Skip ----
        if not antwort and not bild_antwort:
            if not request.session.get("warte_auf_weiter"):
                messages.info(request, "Letzte Aufgabe übersprungen.")
            request.session["index"] += 1
            request.session.pop('aktiver_index', None)
            request.session["warte_auf_weiter"] = False
            request.session.pop("letzte_antwort", None)
            return redirect("physik:aufgaben")

        ergebnis = bewerte_aufgabe(
            request,
            aufgabe,
            antwort,
            text_antwort=antwort,
            bild_antwort=bild_antwort,
            session=request.session,
        )

        print(f"DEBUG: ergebnis = {ergebnis}")

        # ---- richtig ----
        if ergebnis.get("richtig"):
            print("DEBUG: Antwort wurde als RICHTIG bewertet (keine KI-Prüfung)")
            messages.success(request, ergebnis.get("hinweis", "Richtig!"))
            request.session["index"] += 1
            request.session.pop('aktiver_index', None)
            request.session["warte_auf_weiter"] = False
            request.session.pop("letzte_antwort", None)
            return redirect("physik:aufgaben")  # ⬅ FIX 1: sonst wird unten die alte Aufgabe erneut gerendert

        # ---- ungültig ----
        elif ergebnis.get("ungueltig"):
            messages.warning(request, ergebnis["hinweis"])
            request.session["warte_auf_weiter"] = False
            request.session.pop("letzte_antwort", None)

        # ---- falsch ----
        else:
            print("DEBUG: Antwort wurde als FALSCH bewertet (KI-Prüfung möglich)")
            hinweis_text = ergebnis.get("hinweis", "Leider falsch.")

            # KI-Zweite Bewertung für Freitext-Aufgaben
            if aufgabe.typ not in ["p", "a", "r", "w", "x"] and ("o" in aufgabe.typ or "u" in aufgabe.typ):

                # ⬅ FIX 2: KI-Aufruf absichern, damit ein API-Fehler die Seite nicht zum Absturz bringt
                try:
                    ki_ergebnis = check_answer_with_api(
                        aufgabe.frage,
                        aufgabe.loesung,
                        antwort,
                        typ=aufgabe.typ,
                        optionen=aufgabe.optionen.all(),
                        kategorie=aufgabe.thema.thema if aufgabe.thema else "Unbekannt",
                        kapitel=aufgabe.kapitel.kapitel if aufgabe.kapitel else "Unbekannt"
                    )
                except RuntimeError as e:
                    print(f"[WARN] KI-Check fehlgeschlagen: {e}")
                    messages.warning(request, "Die KI-Prüfung ist gerade nicht erreichbar. " + hinweis_text)
                    ki_ergebnis = None

                fehler_log_id = request.session.get("fehler_log_id")

                if ki_ergebnis == "stimmt":
                    # KI akzeptiert die Antwort → Überschreibe das Ergebnis!
                    ergebnis = {"richtig": True, "hinweis": "Richtig! (KI-Bestätigung)"}

                    # FehlerLog aktualisieren/erstellen
                    if fehler_log_id:
                        fehler_log = FehlerLog.objects.get(pk=int(fehler_log_id))
                        fehler_log.ki_bewertung = True
                        fehler_log.ki_hinweis = f"KI hat die Antwort als inhaltlich richtig bewertet: {ki_ergebnis}"
                        fehler_log.save()
                        request.session.pop("fehler_log_id", None)
                    else:
                        fehler_log = FehlerLog.objects.create(
                            aufgabe=aufgabe,
                            eingegebene_antwort=antwort,
                            ki_bewertung=True,
                            ki_hinweis=f"KI hat die Antwort als inhaltlich richtig bewertet: {ki_ergebnis}"
                        )
                        request.session["fehler_log_id"] = int(fehler_log.pk)

                    messages.success(request, f'Die App hätte eher eine Antwort wie "{aufgabe.loesung}" erwartet.\nIch (die KI) finde deine Antwort "{antwort}" auch gut - vielleicht berücksichtigst du den Lösungsvorschlag des Physiktrainers beim nächsten Mal.\n(KI-Einschätzung)')
                    request.session["index"] += 1
                    request.session.pop('aktiver_index', None)
                    request.session["warte_auf_weiter"] = False
                    request.session.pop("letzte_antwort", None)
                    return redirect("physik:aufgaben")

                elif ki_ergebnis is not None:
                    # KI hat explizit "falsch" bewertet (nicht "stimmt")
                    messages.error(request, f"Leider falsch. {ki_ergebnis}")
                    request.session["warte_auf_weiter"] = False
                    request.session.pop("letzte_antwort", None)

                # bei ki_ergebnis is None (Fehlerfall aus dem except-Block)
                # wurde die Warning oben schon gesetzt, kein weiterer Code nötig

            else:
                # Kein KI-Check für diesen Typ → normale Fehlermeldung anzeigen
                messages.error(request, hinweis_text)
                request.session["warte_auf_weiter"] = False
                request.session.pop("letzte_antwort", None)                
    # -------- GET anzeigen --------
    return render(request, "physik/aufgabe.html", {
        "aufgabe": aufgabe,
        "anmerkung": anmerkung_fuer_template,
        "anzeigen": anzeigen,
        "bilder": bilder_anzeige,
        "auswahl_optionen": optionen_liste,
        "fragenummer": index + 1,
        "anzahl": len(ids_in_session),
        "warte_auf_weiter": request.session.get("warte_auf_weiter", False),
        "letzte_antwort": request.session.get("letzte_antwort", "") 
            if request.session.get("warte_auf_weiter") else "",
    })

@user_passes_test(ist_mitarbeiter, login_url='/physik/anmelden/')
def aufgaben_liste(request):
    themenbereiche = ThemenBereich.objects.all()
    thema_id = request.GET.get('thema')
    kapitel_id = request.GET.get('kapitel')
    suche = request.GET.get('q') # Das neue Suchfeld abgreifen

    # Kapitel für den Filter laden
    if thema_id:
        kapitel_liste = Kapitel.objects.filter(thema_id=thema_id).order_by('zeile')
    else:
        kapitel_liste = Kapitel.objects.all().order_by('thema', 'zeile')

    # Basis-Abfrage
    aufgaben = Aufgabe.objects.select_related('kapitel__thema').all().order_by('kapitel__thema', 'lfd_nr')
    
    # Filterung nach Thema/Kapitel
    if thema_id:
        aufgaben = aufgaben.filter(kapitel__thema_id=thema_id)
    if kapitel_id:
        aufgaben = aufgaben.filter(kapitel_id=kapitel_id)
        
    # NEU: Die Suche nach dem Namenskürzel oder Text
    if suche:
        aufgaben = aufgaben.filter(lfd_nr__icontains=suche)
    return render(request, 'physik/aufgaben_liste.html', {
        'aufgaben': aufgaben,
        'themenbereiche': themenbereiche,
        'kapitel_liste': kapitel_liste,
        'suche': suche, # Damit das Suchwort im Feld stehen bleibt
    })

@user_passes_test(ist_mitarbeiter, login_url='/physik/anmelden/')
def aufgabe_einstellungen(request, pk):
    # Holt die Aufgabe oder zeigt 404, wenn die ID nicht existiert
    aufgabe = get_object_or_404(Aufgabe, pk=pk)
    return render(request, 'physik/aufgabe_einstellungen.html', {'aufgabe': aufgabe})

@user_passes_test(ist_mitarbeiter, login_url='/physik/anmelden/')
def call(request, lfd_nr):
    try:
        aufgabe = Aufgabe.objects.get(lfd_nr=lfd_nr)
    except Aufgabe.DoesNotExist:
        try:
            aufgabe = Aufgabe.objects.get(lfd_nr__iexact=lfd_nr)
        except Aufgabe.DoesNotExist:
            return HttpResponse(f"Aufgabe mit der Bezeichnung '{lfd_nr}' wurde nicht gefunden.")
    request.session.pop('aktiver_index', None)

    request.session["aufgaben_ids"] = [aufgabe.id]
    request.session["index"] = 0
    request.session["warte_auf_weiter"] = False
    request.session.pop("letzte_antwort", None)

    return redirect("physik:aufgaben")

@user_passes_test(ist_mitarbeiter, login_url='/physik/anmelden/')
def fehler_liste(request):
    # Basis-Queryset
    logs = FehlerLog.objects.all().select_related('aufgabe__thema', 'aufgabe__kapitel')
    # --- NEU: Sortierung ---
    sort = request.GET.get('sort', '-id')  # Standard: Neueste Fehlermeldungen oben
    if sort == 'fachlich':
        # Sortiert nach Thema-Reihenfolge -> Kapitel-Reihenfolge -> Aufgabennummer
        #logs = logs.order_by('aufgabe__thema__ordnung', 'aufgabe__kapitel__ordnung', 'aufgabe__lfd_nr')
        logs = logs.order_by('aufgabe__thema__ordnung', 'aufgabe__lfd_nr')

    else:
        logs = logs.order_by('-id')
    # 1. Suche (lfd_nr oder Frage)
    q = request.GET.get('q')
    if q:
        logs = logs.filter(
            Q(aufgabe__lfd_nr__icontains=q) | 
            Q(aufgabe__frage__icontains=q) |
            Q(eingegebene_antwort__icontains=q)
        )

    # 2. Filter nach Thema
    thema_id = request.GET.get('thema')
    if thema_id:
        logs = logs.filter(aufgabe__thema_id=thema_id)

    # 3. Filter nach Kapitel
    kapitel_id = request.GET.get('kapitel')
    if kapitel_id:
        logs = logs.filter(aufgabe__kapitel_id=kapitel_id)

    # Daten für die Dropdowns
    themen = ThemenBereich.objects.all().order_by('ordnung')
    # Kapitel nur für das gewählte Thema (optional, für bessere UX)
    kapitel = Kapitel.objects.filter(thema_id=thema_id) if thema_id else Kapitel.objects.all()

    context = {
        'logs': logs,
        'themen': themen,
        'kapitel': kapitel,
        's_thema': int(thema_id) if thema_id else None,
        's_kapitel': int(kapitel_id) if kapitel_id else None,
        'query': q or '',
        'sort': sort,
    }
    return render(request, 'physik/fehler_liste.html', context)

@user_passes_test(ist_mitarbeiter, login_url='/physik/anmelden/')
def fehler_edit(request, log_id):
    # Wir holen das log trotzdem am Anfang, um sicherzugehen, dass es existiert
    log = get_object_or_404(FehlerLog, id=log_id)
    aufgabe = log.aufgabe

    if request.method == "POST":
        if "just_delete" in request.POST:
            # Anstatt log.delete() nutzen wir den Filter:
            FehlerLog.objects.filter(id=log_id).delete()
            # Danach ein Redirect, da das Objekt 'log' nicht mehr sicher nutzbar ist
            return redirect("physik:fehler_liste") 
        else:
            # 1. Hauptfelder der Aufgabe speichern
            aufgabe.typ = request.POST.get("typ")
            aufgabe.frage = request.POST.get("frage")
            aufgabe.loesung = request.POST.get("antwort")
            aufgabe.anmerkung = request.POST.get("anmerkung")
            aufgabe.erklaerung = request.POST.get("erklaerung")
            aufgabe.hilfe = request.POST.get("hilfe")
            aufgabe.save()

            # 2. Bestehende Optionen aktualisieren oder löschen
            for key, value in request.POST.items():
                if key.startswith("opt_"):
                    opt_id = key.split("_")[1]
                    option = AufgabeOption.objects.get(id=opt_id)
                    
                    if value.strip(): 
                        option.text = value.strip()
                        option.save()
                    else: # Falls Text leer: Weg damit
                        option.delete()

            # 3. Neue Optionen anlegen (die 3 leeren Felder)
            for i in range(1, 4):
                new_text = request.POST.get(f"new_opt_{i}")
                
                if new_text and new_text.strip():
                    # Wir ignorieren new_pos aus dem POST und berechnen es selbst:
                    # Suche die höchste vorhandene Position für diese Aufgabe
                    last_opt = AufgabeOption.objects.filter(aufgabe=aufgabe).order_by('-position').first()
                    
                    # Start bei 2, wenn noch nichts da ist (wegen offizieller Antwort = 1)
                    next_pos = (last_opt.position + 1) if last_opt else 2
                    
                    AufgabeOption.objects.create(
                        aufgabe=aufgabe,
                        text=new_text.strip(),
                        position=next_pos
                    )

        # Erst wenn alles gespeichert ist, löschen wir den Fehler-Log
        log.delete()

        return redirect('physik:fehler_liste')

    return render(request, 'physik/fehler_edit.html', {'log': log})

def howto(request):
    return render(request, 'physik/howto.html')

def datenschutz(req):
    return render(req, 'physik/datenschutz.html', context={'titel': "Datenschutz",})