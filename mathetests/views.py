import random
from decimal import Decimal
from collections import defaultdict

from django.shortcuts import render, get_object_or_404, redirect
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseBadRequest
from django.db import transaction
from django.db.models import Count, Sum, Case, Q, When, IntegerField
from django.utils import timezone
from django.contrib import messages
from django.urls import reverse
from django.views.decorators.http import require_POST

from accounts.models import Profil, Lerngruppe

from core.models import Kategorie, Auswahl, Protokoll, Zaehler
from core.views import get_profil, aufgaben, kontrolle
from core.forms import AufgabeFormZahl, AufgabeFormStr, AufgabeFormTab, AufgabeFormTerm

from .models import Test, TestEinstellung
from .forms import TestErstellenForm, TestNameForm

from .models import Test
from .forms import ProtokollBewertungForm

from .utilities import kurs_to_stufe, berechne_note, slots_pro_tabelle, werte_aus_wertung, build_soll_map, analyse_protokolle, berechne_quote_und_note

def test_how_to(req):
    return render(req, "tests/test_how_to.html",)

# ---------- Schritt 1: Kategorien + Optionen erfassen ----------
def test_erstellen(req, gruppe_id):
    gruppe = get_object_or_404(Lerngruppe, pk=gruppe_id)
    if gruppe.lehrer != req.user and not req.user.is_superuser:
        return HttpResponseForbidden("Zugriff verweigert")
    kategorien = Kategorie.objects.order_by("zeile")
    if req.method == "POST":
        form = TestErstellenForm(req.POST, kategorien=kategorien)
        if form.is_valid():
            positionen = []
            for kat in kategorien:
                anzahl = form.cleaned_data.get(f"kat_{kat.pk}_anzahl") or 0
                auswahl_ids = form.cleaned_data.get(f"kat_{kat.pk}_opts", [])
                if anzahl > 0 or auswahl_ids:
                    positionen.append({
                        "kat_id": kat.id,
                        "anzahl": int(anzahl),
                        "auswahl_ids": [int(x) for x in auswahl_ids],
                    })
            # Draft in der Session ablegen -> wird in test_benennen verwendet
            req.session["test_draft"] = {
                "gruppe_id": gruppe.id,
                "positionen": positionen,
            }
            return redirect("test_benennen", gruppe_id=gruppe.id)
    else:
        form = TestErstellenForm(kategorien=kategorien)
    zeilen = []
    for kat in kategorien:
        feld_anz = form[f"kat_{kat.pk}_anzahl"]
        slots = slots_pro_tabelle(kat)
        feld_opt = form[f"kat_{kat.pk}_opts"] if f"kat_{kat.pk}_opts" in form.fields else None
        zeilen.append((kat, feld_anz, slots, feld_opt))
    return render(req, "tests/test_erstellen.html", {
        "gruppe": gruppe,
        "zeilen": zeilen,
    })

# ---------- Schritt 2: Test benennen & speichern ----------
def test_benennen(req, gruppe_id):
    gruppe = get_object_or_404(Lerngruppe, pk=gruppe_id)
    draft = req.session.get("test_draft")
    if not draft:
        return HttpResponseBadRequest("Kein Test-Entwurf vorhanden.")
    if req.method == "POST":
        form = TestNameForm(req.POST)
        if form.is_valid():
            name = form.cleaned_data["name"]
            note_modus = form.cleaned_data["note_modus"]
            schwierigkeit = form.cleaned_data["schwierigkeit"]
            with transaction.atomic():
                test = Test.objects.create(
                    gruppe=gruppe,
                    name=name,
                    note_streng=(note_modus == "normal"),
                    schwierigkeit=schwierigkeit,
                )
                jg = getattr(gruppe, "jg", 0)
                stufe = kurs_to_stufe(schwierigkeit)
                for pos in draft["positionen"]:
                    kat = Kategorie.objects.get(pk=pos["kat_id"])
                    if pos["auswahl_ids"]:
                        texts = (Auswahl.objects
                                 .filter(pk__in=pos["auswahl_ids"])
                                 .values_list("text", flat=True))
                        optionen_text = ", ".join(texts)
                    else:
                        optionen_text = "keine"
                    ret = aufgaben(
                        kategorie_id=kat.zeile,
                        optionen=optionen_text,
                    )
                    if not isinstance(ret, tuple):
                        typ_anf, typ_end, reihenfolge = 0, 0, None
                    else:
                        if len(ret) == 3:
                            typ_anf, typ_end, reihenfolge = ret
                        elif len(ret) == 2:
                            typ_anf, typ_end = ret
                            reihenfolge = None
                        else:
                            typ_anf, typ_end, reihenfolge = 0, 0, None
                    TestEinstellung.objects.create(
                        test=test,
                        kategorie=kat,
                        anzahl=pos["anzahl"],
                        optionen_text=optionen_text,
                        typ_anf=typ_anf,
                        typ_end=typ_end,
                        reihenfolge=reihenfolge,
                    )
                del req.session["test_draft"]
                return redirect("gruppe_uebersicht", gruppe_id=gruppe.id)
    else:
        form = TestNameForm()
    return render(req, "tests/test_benennen.html", {"gruppe": gruppe, "form": form})

# ---------- Schritt 3: Test anzeigen ----------
def test_anzeigen(req, test_id, profil_id):
    test = get_object_or_404(Test, pk=test_id)
    gruppe = test.gruppe
    # Profil des Schülers
    profil = (
        Profil.objects
        .filter(id=profil_id)
        .select_related("gruppe")
        .first()
    )
    user_profil = getattr(req.user, "profil", None)

    # --- Zugriff prüfen ---
    if not (user_profil == profil or req.user == gruppe.lehrer or req.user.is_superuser):
        return HttpResponse("Zugriff verweigert")
    if not profil or profil.gruppe_id != gruppe.id:
        return render(req, "schueler/keine_gruppe.html", {"titel": "kein Zugriff"})
    # --- Testeinstellungen / Kategorien ---
    einstellungen = (
        TestEinstellung.objects
        .filter(test=test)
        .select_related("kategorie")
        .order_by("kategorie__zeile")
    )
    # Soll-Slots pro Kategorie (inkl. Wertetabellen)
    soll_map, total_soll_global = build_soll_map(einstellungen)

    # --- Protokolle dieses Schülers für diesen Test ---
    prot = (
        Protokoll.objects
        .filter(profil=profil, hilfe_id=test.proto_marker)
        .select_related("kategorie")
        .order_by("-start")
    )
    if prot.exists():
        test_datum = prot.order_by("start").first().start.date()
    else:
        test_datum = None
    # Slot-Analyse aus wertung (für obere Tabelle & Zähler)
    analysis = analyse_protokolle(prot, soll_map)
    # 1. Summen pro Kategorie für die Tabelle oben (nur aus wertung!)
    protos_by_kat = defaultdict(list)
    for p in prot:
        protos_by_kat[p.kategorie_id].append(p)

    zeilen = []
    for e in einstellungen:
        kat = e.kategorie
        kat_id = kat.id

        soll = soll_map.get(kat_id, 0)

        kat_stats = analysis["pro_kat"].get(kat_id, {"r": 0, "f": 0, "x": 0})
        richtig_slots = kat_stats["r"]
        falsch_slots = kat_stats["f"]
        erledigt_slots = richtig_slots + falsch_slots

        # Abbrüche / „Lsg anzeigen“ pro Kategorie (ändern wertung NICHT!)
        kat_prots = protos_by_kat.get(kat_id, [])
        abbr_aufg = 0
        lsg_aufg = 0
        for p in kat_prots:
            if p.abbr:
                abbr_aufg += 1
            if p.lsg:
                lsg_aufg += 1

        offen = max(soll - erledigt_slots, 0)

        zeilen.append({
            "kat": kat,
            "soll": soll,
            "erledigt": erledigt_slots,
            "offen": offen,
            "richtig": richtig_slots,
            "falsch": falsch_slots,
            "abbr": abbr_aufg,
            "lsg": lsg_aufg,
            "darf_starten": test.aktiv and offen > 0,
        })

    # Gesamtsummen für Zählerzeile (alles Slots / wertung-basiert)
    gesamt_abbr = sum(z["abbr"] for z in zeilen)
    gesamt_lsg  = sum(z["lsg"] for z in zeilen)

    gesamt = {
        "soll":     analysis["total_soll"],
        "erledigt": analysis["erledigt_sum"],
        "offen":    analysis["offen"],
        "richtig":  analysis["r_sum"],
        "falsch":   analysis["f_sum"],
        "abbr":     gesamt_abbr,
        "lsg":      gesamt_lsg,
    }
    gesamt_soll   = gesamt["soll"]
    gesamt_offen  = gesamt["offen"]
    aufg_richtig  = analysis["r_sum"]
    aufg_falsch   = analysis["f_sum"]
    # ------------------------------------------------------------------
    # 2. Punkte / Quote / Note (nur p.richtig / p.falsch + Abbr/Lsg)
    #    => hier greifen manuelle Änderungen des Lehrers!
    # ------------------------------------------------------------------
    quote_info = berechne_quote_und_note(
        analysis=analysis,
        protos=prot,
        test=test,
    )
    # ------------------------------------------------------------------
    # 3. Notenspiegel (für Schülerseite)
    #    -> für jeden Schüler: Slot-Analyse + Punkte-Logik wie oben
    # ------------------------------------------------------------------
    noten_spiegel_s = None
    noten_durchschnitt_s = None

    if not test.aktiv:
        noten_spiegel_s = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
        noten_summe = 0
        noten_anzahl = 0
        for sch in Profil.objects.filter(gruppe=gruppe):
            prot_s = (
                Protokoll.objects
                .filter(profil=sch, hilfe_id=test.proto_marker)
                .select_related("kategorie")
            )
            if not prot_s.exists():
                continue
            analysis_s = analyse_protokolle(prot_s, soll_map)
            qinfo_s = berechne_quote_und_note(
                analysis=analysis_s,
                protos=prot_s,
                test=test,
            )
            note_s = qinfo_s["note"]
            if not note_s:
                continue
            try:
                basis = int(note_s[0])
            except (ValueError, TypeError):
                continue
            if basis in noten_spiegel_s:
                noten_spiegel_s[basis] += 1
                noten_summe += basis
                noten_anzahl += 1
        if noten_anzahl > 0:
            noten_durchschnitt_s = round(noten_summe / noten_anzahl, 1)
    # ------------------------------------------------------------------
    # 4. Context für Template
    # ------------------------------------------------------------------
    context = {
        "test": test,
        "profil": profil,
        "gruppe": gruppe,
        "zeilen": zeilen,
        "zeilen_gesamt": gesamt,
        "prot": prot,
        "test_datum": test_datum,

        # Zähler-Zeile (Aufgaben = Slots aus wertung)
        "gesamt_soll": gesamt_soll,
        "gesamt_offen": gesamt_offen,
        "gesamt_abbr": gesamt_abbr,
        "gesamt_lsg": gesamt_lsg,
        "aufg_richtig": float(aufg_richtig),
        "aufg_falsch": float(aufg_falsch),
        # Punkte-Zeile (aus p.richtig/p.falsch + Abbr/Lsg)
        "richtig_punkte": quote_info["richtig_punkte"],
        "cheat_punkte": quote_info["cheat_punkte"],
        "abbr_punkte": quote_info["abbr_punkte"],
        "lsg_punkte": quote_info["lsg_punkte"],
        "sum_quote": quote_info["quote"],

        "note": quote_info["note"],
        "noten_spiegel_s": noten_spiegel_s,
        "noten_durchschnitt_s": noten_durchschnitt_s,
    }

    return render(req, "tests/test_anzeigen.html", context)

# ---------- Schritt 4: Test bearbeiten ----------
def test(req, slug):
    # ---------------- Sicherheit -----------------
    if not req.user.is_authenticated:
        return redirect("anmelden")
    kategorie = get_object_or_404(Kategorie, slug=slug)
    profil = req.user.profil
    # Test-ID holen
    test_id = req.GET.get("test")
    if not test_id:
        return redirect("index")
    test = get_object_or_404(Test, pk=test_id)
    # Gruppenzugehörigkeit prüfen
    if profil.gruppe_id != test.gruppe_id:
        return render(req, "schueler/keine_gruppe.html", {"titel": "kein Zugriff"})
    # Einstellungen für diese Kategorie
    cheat = False
    einstellung = get_object_or_404(TestEinstellung, test=test, kategorie=kategorie)
    slots = slots_pro_tabelle(kategorie)
    soll_anzahl = einstellung.anzahl + slots -1
    # Bisher erledigte Aufgaben in diesem Test (über wertung = r/f)
    protos_kat = Protokoll.objects.filter(
        profil=profil,
        kategorie=kategorie,
        hilfe_id=test.proto_marker,
    )
    erledigt_kat = 0
    for p in protos_kat:
        w = p.wertung or ""
        # nur echte Aufgaben-Slots zählen: r oder f
        erledigt_kat += w.count("r") + w.count("f")

    # ---------------- Kategorie abgeschlossen? ----------------
    # Wenn Aufgabe falsch war und dies die letzte Aufgabe der Kategorie ist:
    if erledigt_kat >= soll_anzahl:
        # --- Kategorie-Statistik berechnen ---
        stats = (
            Protokoll.objects
            .filter(
                profil=profil,
                kategorie=kategorie,
                hilfe_id=test.proto_marker
            )
            .aggregate(
                richtig_anz=Sum(
                    Case(
                        When(abbr=False, lsg=False, richtig__gt=0, then=1),
                        default=0,
                        output_field=IntegerField()
                    )
                ),
                falsch_anz=Sum(
                    Case(
                        When(abbr=False, lsg=False, richtig=0, falsch__gt=0, then=1),
                        default=0,
                        output_field=IntegerField()
                    )
                ),
                abbr_anz=Sum(
                    Case(
                        When(abbr=True, then=1),
                        default=0,
                        output_field=IntegerField()
                    )
                ),
                lsg_anz=Sum(
                    Case(
                        When(lsg=True, then=1),
                        default=0,
                        output_field=IntegerField()
                    )
                ),
            )
        )

        context = {
            "kat": kategorie,
            "soll": soll_anzahl,
            "richtig": stats["richtig_anz"] or 0,
            "falsch": stats["falsch_anz"] or 0,
            "abbr": stats["abbr_anz"] or 0,
            "lsg": stats["lsg_anz"] or 0,
            "test": test,
            "profil": profil,
        }

        return render(req, "tests/kategorie_fertig.html", context)
    if req.method == "POST":
        tabelle = richtig = 0
        protokoll_id = req.POST.get("protokoll_id")
        protokoll = get_object_or_404(Protokoll, pk=protokoll_id)
        zaehler_id = req.POST.get("zaehler_id")
        # passendes Formular bestimmen
        if "tab" in protokoll.parameter.get("name", ""):
            if "term" in protokoll.parameter.get("name", ""):
                form = AufgabeFormTerm(req.POST)
            else:
                form = AufgabeFormTab(req.POST)
        else:
            form = AufgabeFormZahl(req.POST) if protokoll.wert else AufgabeFormStr(req.POST)
        # --------- FORMULAR NICHT GÜLTIG -----------
        if not form.is_valid():
            if "tab" in protokoll.parameter["name"]:                            # für Wertetabellen
                messages.info(req, 'Da stimmt was mit deiner Eingabe nicht. <br>In eine Wertetabelle gehören z.B. keine Buchstaben rein.')
            else:
                messages.info(req, 'Da stimmt was mit deiner Eingabe nicht. <br>Möglicherweise ist deine Eingabe zu lang.')
            # aktuelle Aufgabe erneut anzeigen
            return render(req, "tests/test_aufgabe.html", {
                "kategorie": protokoll.kategorie,
                "titel": protokoll.titel,
                "aufgnr": protokoll.aufgnr,
                "soll": soll_anzahl,
                "text": protokoll.text,
                "frage": protokoll.frage,
                "einheit": protokoll.einheit,
                "parameter": protokoll.parameter,
                "form": form.__class__(),   # leeres Formular
                "message_unten": protokoll.anmerkung,
                "lsg": False,
                "eingabe": "",
                "protokoll_id": protokoll.id,
                "test_id": test.id,
            })
        # ============== FORMULAR GÜLTIG – KONTROLLE =============
        # Eingabe auslesen
        if "tab" in protokoll.parameter.get("name", ""):
            eingabe_liste = []
            if "term" in protokoll.parameter.get("name", ""):
                eingabe_liste.append(form.cleaned_data["y0"])
                eingabe_liste.append(form.cleaned_data["y1"])
            eingabe_liste.append(form.cleaned_data["y2"])
            eingabe_liste.append(form.cleaned_data["y3"])
            eingabe_liste.append(form.cleaned_data["y4"])
            pro_eingabe = "; ".join(str(e) for e in eingabe_liste).replace(".", ",")
            eingabe = eingabe_liste          # für kontrolle()
        else:
            eingabe = form.cleaned_data["eingabe"]
            pro_eingabe = eingabe
        # ins Protokoll den String für die Anzeige
        protokoll.eingabe = pro_eingabe
        protokoll.abbr = False
        protokoll.end = timezone.now()
        protokoll.save()
        # Kontrolle aufrufen
        wertung, rueckmeldung = kontrolle(
            eingabe,            # bei Tabelle: Liste, sonst String
            protokoll.wert,
            protokoll.loesung,
            protokoll.id,
        )
        # =============== WERTUNG = 0 (Eingabe-Fehler) ==================
        if wertung == 0:
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
            messages.info(req, rueckmeldung)
            # Aufgabe aus dem Protokoll neu laden
            titel = protokoll.titel
            text = protokoll.text
            pro_text = protokoll.pro_text
            parameter = protokoll.parameter
            frage = protokoll.frage
            einheit = protokoll.einheit
            anmerkung = protokoll.anmerkung
            loesung = protokoll.loesung
            return render(req, "tests/test_aufgabe.html", {
                "test_id": test_id,
                "zaehler_id": zaehler_id,
                "protokoll_id": protokoll.id,
                "kategorie": kategorie,
                "form": form,
                # Aufgabe aus Protokoll wieder anzeigen
                "titel": titel,
                "text": text,
                "pro_text": pro_text,
                "frage": frage,
                "einheit": einheit,
                "anmerkung": anmerkung,
                "parameter": parameter,
                "loesung": loesung,

            })
        # -------- Tabelle oder normal? ----------
        if wertung <= 2:
            tabelle = 0
            richtig = wertung
            if "halben Extra" in rueckmeldung:
                protokoll.wertung = protokoll.wertung + "x"
                protokoll.save()
            elif "Extra" in rueckmeldung:
                protokoll.wertung = protokoll.wertung + "xx"
                protokoll.save()
        else:
            if wertung >= 3000:
                tabelle = 3
                richtig = str(wertung).count("1")
                falsch = str(wertung).count("0")
                if str(wertung).count("2")>0:
                    protokoll.abbr = True
                    protokoll.save()
            if wertung >= 30000:
                tabelle = 4
            if wertung >= 300000:
                tabelle = 5
        # ================ RICHTIG ====================
        if (wertung > 0 and tabelle == 0) or (tabelle > 0 and richtig == tabelle):
            if tabelle > 0:
                # komplettes Tabellenrichtig
                protokoll.wertung = "r" * richtig
                rueckmeldung = "Alle Werte waren richtig."
                protokoll.richtig = richtig    # z.B. 3 richtige Felder
                protokoll.falsch = 0
            elif tabelle == 0 :
                if "enauer" in rueckmeldung:
                    rueckmeldung = "Die letzte Aufgabe war fast richtig."+ rueckmeldung
                else:
                    rueckmeldung = "Die letzte Aufgabe war richtig."+ rueckmeldung
                protokoll.wertung = protokoll.wertung + "r"
            if protokoll.lsg:
                cheat = True
            if cheat:
                protokoll.falsch = 2
                protokoll.wertung = "f"
                protokoll.eingabe = "Cheat: Lösung wurde aufgerufen"
                messages.warning(req, f'Das habe ich gemerkt!<br>Du hast geschummelt, du hast die Lösung aufgerufen. Die Eingabe stimmt zwar, die Aufgabe wird aber als Doppelfehler gewertet!')
            else:
                if wertung < 10:                # damit nicht die Wertung (zb 3111) aus Wertetabelle mit nicht komplett richtigen Eingaben gespeichert wird
                    protokoll.richtig = richtig 
                protokoll.abbr = False 
                protokoll.lsg = False
                messages.info(req, rueckmeldung)
            protokoll.save()
            # neue Aufgabe
            return redirect(f"{req.path}?test={test.id}")
        # ================ FALSCH ====================
        else:
            parameter = protokoll.parameter
            if tabelle > 0:
                # protokoll.wertung = (str(wertung)[1:]
                #                       .replace("1", "r")
                #                       .replace("0", "f")
                #                       .replace("2", "/"))
                # protokoll.falsch = falsch
                # protokoll.richtig = richtig
                str_wertung = (str(wertung)[1:]).replace("1","r").replace("0","f").replace("2","/")
                protokoll.wertung = str_wertung
                if protokoll.falsch < falsch:
                    protokoll.falsch = falsch
                protokoll.richtig = richtig
                protokoll.save()
                messages.info(req, f'{rueckmeldung}')
                color_wertung = (str(wertung)[1:]).replace("1","richtig,").replace("0","falsch,").replace("2","leer,")
                color_wertung =color_wertung[:-1].split(",")
                y_farbe = {}
                if tabelle >3:
                    for n in range (0,tabelle):
                        y_farbe["color" + str(n)] = color_wertung[tabelle-1-n]
                else:
                    for n in range (0,tabelle):
                        y_farbe["color" + str(n+2)] = color_wertung[tabelle-1-n]
                parameter.update(y_farbe)
            else:
                protokoll.wertung = "f"
                protokoll.falsch = 1
                if wertung < 0:                             #wenn mithilfe des Eintrags "indiv_1" ein Teilpunkt vergeben wurde, wird dies hier angezeigt:
                    messages.info(req, rueckmeldung)  
                    wertung = -1      
                if wertung == -1:
                    protokoll.falsch = 1
                    protokoll.wertung = "f"
                    messages.info(req, f'Die letzte Aufgabe war leider falsch.')
                else:
                    if not "tab" in protokoll.parameter["name"]:
                        messages.info(req, f'{rueckmeldung}')   #gibt eine Rückmeldung wenn "indiv" bei Lösung steht  
            protokoll.save()
            text = "Richtig wäre die Lösung: {0}<br>Deine Eingabe: {1}.".format(protokoll.loesung[0],str(protokoll.eingabe).replace(".",","))
            messages.info(req, text) 
            # nächste Aufgabe
            return redirect(f"{req.path}?test={test.id}")
    # ===============================================================
    # GET → neue Aufgabe erzeugen
    # ===============================================================
    aufgnr = erledigt_kat + 1
    # Zähler minimal benötigt wegen sachaufgaben
    zaehler, _ = Zaehler.objects.get_or_create(profil=profil, kategorie=kategorie)
    if kategorie.slug == "sachaufgaben":
        zaehler.letzter_typ = (zaehler.letzter_typ or 0) + 1
        zaehler.save()
        typ_anf = zaehler.letzter_typ
    else:
        typ_anf = einstellung.typ_anf
    typ_end = einstellung.typ_end
    reihenfolge = einstellung.reihenfolge or None
    # ---------------- Aufgabe erzeugen ----------------
    # Stufe aus Test / TestEinstellung ableiten
    schwierigkeit = getattr(einstellung, "schwierigkeit", None) or test.schwierigkeit
    stufe = kurs_to_stufe(schwierigkeit)
    # Sonderfall: zusätzliche Aufgaben für Gymnasium / A-Kurs
    if kategorie.name in ("Prozentrechnung", "Bruchteile", "Funktionen") and schwierigkeit in ("A", "Y"):
        stufe += 0.2
    # Jahrgang lieber aus der Gruppe nehmen (alle in der Lerngruppe gleich)
    jg = getattr(test.gruppe, "jg", profil.jg)
    typ, typ2, titel, text, pro_text, frage, variable, einheit, anmerkung, \
    lsg, hilfe_id, ergebnis, parameter = aufgaben(kategorie.zeile, jg=jg, stufe=stufe, aufgnr=aufgnr, typ_anf=typ_anf, typ_end=typ_end, reihenfolge=reihenfolge, optionen="",)
    slots = slots_pro_tabelle(kategorie)
    if slots > 1:
        lsg = ([lsg[0][:slots]])
    if kategorie.slug == "sachaufgaben":
        zaehler.letzter_typ = typ
        zaehler.save()
    text = text.format(*variable)
    if pro_text:
        pro_text = pro_text.format(*variable)
    frage = frage.format(*variable)
    # Protokoll speichern
    protokoll = Protokoll.objects.create(
        profil=profil,
        titel=titel,
        sj=profil.sj,
        hj=profil.hj,
        kategorie=kategorie,
        text=text,
        pro_text=pro_text,
        variable=variable,
        frage=frage,
        einheit=einheit,
        anmerkung=anmerkung,
        wert=ergebnis,
        loesung=lsg,
        hilfe_id=test.proto_marker,
        parameter=parameter,
        wertung="a",
        typ=typ,
        typ2=typ2,
        aufgnr=aufgnr,
    )
    # Formular bestimmen
    if "tab" in parameter.get("name", ""):
        form = AufgabeFormTerm() if "term" in parameter.get("name", "") else AufgabeFormTab()
    else:
        form = AufgabeFormZahl() if ergebnis else AufgabeFormStr()
    # ===== Notenspiegel für die Schülerseite =====
    # nur berechnen, wenn der Test beendet ist
    noten_spiegel_s = None
    noten_durchschnitt_s = None
    if not test.aktiv:
        noten_spiegel_s = {1:0,2:0,3:0,4:0,5:0,6:0}
        noten_summe = 0
        noten_anzahl = 0
        for sch in Profil.objects.filter(gruppe=req.lerngruppe):
            # alle protokolle dieses Schülers zu diesem Test
            prot_s = Protokoll.objects.filter(
                profil=sch, hilfe_id=test.proto_marker
            )
            if not prot_s.exists():
                continue
            agg_s = prot_s.aggregate(
                rsum=Sum("richtig"),
                fsum=Sum("falsch"),
                ab=Sum(Case(When(abbr=True, then=1), default=0, output_field=IntegerField())),
                lg=Sum(Case(When(lsg=True,  then=1), default=0, output_field=IntegerField())),
            )
            r_p = Decimal(agg_s["rsum"] or 0)
            f_p = Decimal(agg_s["fsum"] or 0)
            ab = agg_s["ab"] or 0
            lg = agg_s["lg"] or 0
            # erledigte Aufgaben
            erledigt_s = prot_s.filter(abbr=False, lsg=False)
            r_a = erledigt_s.filter(richtig__gt=0).count()
            f_a = erledigt_s.filter(richtig=0, falsch__gt=0).count()
            # soll
            total_soll_s = sum(e.anzahl for e in einstellung)
            offen_s = max(total_soll_s - (r_a + f_a), 0)
            fehler_s = f_p + Decimal("0.5") * Decimal(ab + lg) + Decimal(offen_s)
            max_p_s = r_p + fehler_s
            if max_p_s == 0:
                continue
            quote_s = (r_p / max_p_s) * 100
            if protokoll.count() > 0:
                note_s, zusatz = berechne_note(quote_s, test.note_streng)
                # → Eintragen
                noten_spiegel_s[note_s] += 1
                noten_summe += note_s
                noten_anzahl += 1
            else:
                note_s = None
                zusatz = ""
        if noten_anzahl > 0:
            noten_durchschnitt_s = round(noten_summe / noten_anzahl, 1)
    context = {
        "kategorie": kategorie,
        "titel": titel,
        "aufgnr": aufgnr,
        "soll": soll_anzahl,
        "text": text,
        "frage": frage,
        "einheit": einheit,
        "parameter": parameter,
        "form": form,
        "message_unten": anmerkung,
        "lsg": False,
        "eingabe": "",
        "zaehler_id": zaehler.id,
        "protokoll_id": protokoll.id,
        "test_id": test.id,
    }
    return render(req, "tests/test_aufgabe.html", context)

def kategorie_fertig(req):
    context = {}
    return render(req, "tests/kategorie_fertig.html", context)    

def test_uebersicht(req, test_id):
    test = get_object_or_404(Test, pk=test_id)
    gruppe = test.gruppe

    # Nur der zuständige Lehrer oder Superuser
    if gruppe.lehrer != req.user and not req.user.is_superuser:
        return HttpResponseForbidden("Zugriff verweigert")
    # Kategorien dieses Tests (inkl. Soll-Anzahl je Kategorie)
    einstellungen = (
        TestEinstellung.objects
        .filter(test=test)
        .select_related("kategorie")
        .order_by("kategorie__zeile")
    )
    # Slot-Soll pro Kategorie (inkl. Wertetabellen) – gleich wie in Schüleransicht
    soll_map, total_soll_global = build_soll_map(einstellungen)
    # Schüler der Lerngruppe
    schueler_liste = (
        Profil.objects
        .filter(gruppe=gruppe)
        .order_by("nachname", "vorname")
    )
    rows = []
    # Notenspiegel + Durchschnitt sammeln (soll zu Schüleransicht passen!)
    noten_counts = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0}
    noten_sum = 0
    noten_n = 0
    for schueler in schueler_liste:
        # Alle Protokolle dieses Schülers zu diesem Test
        prot_s = (
            Protokoll.objects
            .filter(
                profil=schueler,
                hilfe_id=test.proto_marker,
            )
            .select_related("kategorie")
        )
        # Analyse aus wertung (Slots, Abbr, Lsg, …)
        if prot_s.exists():
            analysis_s = analyse_protokolle(prot_s, soll_map)
        else:
            # keine Protokolle → leere Analyse
            analysis_s = {
                "pro_kat": {},
                "r_sum": 0,
                "f_sum": 0,
                "x_sum": 0,
                "erledigt_sum": 0,
                "abbr": 0,
                "lsg": 0,
                "offen": total_soll_global,
                "total_soll": total_soll_global,
            }
        row = {
            "profil": schueler,
            "kategorien": [],
            "sum_richtig": 0,   # Slots richtig (wertung)
            "sum_falsch": 0,    # Slots falsch  (wertung)
            "sum_erledigt": 0,  # Slots erledigt
            "note": None,
        }
        # --- pro Kategorie: Soll/erledigt/richtig/falsch in Slots ---
        for e in einstellungen:
            kat = e.kategorie
            kat_id = kat.id
            soll_kat = soll_map.get(kat_id, 0)

            kat_stats = analysis_s["pro_kat"].get(kat_id, {"r": 0, "f": 0, "x": 0})
            r_kat = kat_stats["r"]
            f_kat = kat_stats["f"]
            erledigt_kat = r_kat + f_kat

            row["kategorien"].append({
                "kategorie": kat,
                "soll": soll_kat,
                "erledigt": erledigt_kat,
                "richtig": r_kat,
                "falsch": f_kat,
            })
            row["sum_richtig"]  += r_kat
            row["sum_falsch"]   += f_kat
            row["sum_erledigt"] += erledigt_kat
        # --- Gesamtauswertung + Note für diesen Schüler ---
        if prot_s.exists():
            quote_info = berechne_quote_und_note(analysis_s, prot_s, test)
            note_str = quote_info["note"]
        else:
            quote_info = None
            note_str = None
        row["note"] = note_str
        # Notenspiegel zählen (nur Hauptnote 1–6)
        if note_str:
            basis = note_str[0]  # "2" aus "2+"
            try:
                basis_int = int(basis)
            except ValueError:
                basis_int = None
            if basis_int in noten_counts:
                noten_counts[basis_int] += 1
                noten_sum += basis_int
                noten_n += 1
        rows.append(row)
    noten_durchschnitt = (noten_sum / noten_n) if noten_n else None
    context = {
        "test": test,
        "gruppe": gruppe,
        "einstellungen": einstellungen,
        "rows": rows,
        "noten_spiegel": noten_counts,
        "noten_durchschnitt": noten_durchschnitt,
    }
    return render(req, "tests/test_uebersicht_lehrer.html", context)

@require_POST
def test_toggle_aktiv(req, test_id):
    test = get_object_or_404(Test, pk=test_id)
    # nur Lehrer oder Superuser
    if req.user != test.gruppe.lehrer and not req.user.is_superuser:
        return HttpResponse("Kein Zugriff")
    action = req.POST.get("action")
    if action == "start":
        test.aktiv = True
    elif action == "stop":
        test.aktiv = False
    test.save(update_fields=["aktiv"])
    # zurück zur Lehrer-Übersicht
    return redirect("test_uebersicht_lehrer", test_id=test.id)

def bewertung_aendern(req, protokoll_id, ziel):
    prot = get_object_or_404(Protokoll, id=protokoll_id)

    # Nur Lehrkräfte oder Superuser dürfen eingreifen
    user = req.user
    profil = prot.profil
    gruppe = profil.gruppe               # Lerngruppe
    lehrer = gruppe.lehrer               # Lehrkraft der Gruppe

    ist_superuser = user.is_superuser
    ist_zustaendiger_lehrer = (req.user == lehrer)

    if not (ist_superuser or ist_zustaendiger_lehrer):
        return HttpResponseForbidden("Keine Berechtigung.")

    # ziel: "r" = richtig, "f" = falsch
    if ziel == "r":
        prot.richtig = max(prot.richtig, 1)  # mindestens 1 Punkt
        prot.falsch = 0
        prot.abbr = False
        prot.lsg = False
    elif ziel == "f":
        prot.falsch = max(prot.falsch, 1)
        prot.richtig = 0
        prot.abbr = False
        prot.lsg = False

    prot.save()

    # einfach zurück zur vorherigen Seite
    return redirect(req.META.get("HTTP_REFERER", "/"))

@require_POST
def test_toggle_aktiv(req, test_id):
    test = get_object_or_404(Test, pk=test_id)
    # nur Lehrer oder Superuser
    if req.user != test.gruppe.lehrer and not req.user.is_superuser:
        return HttpResponse("Kein Zugriff")
    action = req.POST.get("action")
    if action == "start":
        test.aktiv = True
    elif action == "stop":
        test.aktiv = False
    test.save(update_fields=["aktiv"])
    # zurück zur Lehrer-Übersicht
    return redirect("test_uebersicht_lehrer", test_id=test.id)

def test_loeschen(req, test_id):
    test = get_object_or_404(Test, pk=test_id)

    if req.user != test.gruppe.lehrer and not req.user.is_superuser:
        return HttpResponseForbidden("Kein Zugriff")

    if req.method == "POST":
        test.delete()
        messages.success(req, "Test wurde gelöscht.")
        return redirect("gruppe_uebersicht", gruppe_id=test.gruppe.id)

    return render(req, "tests/test_loeschen_bestaetigen.html", {"test": test})

def abbrechen(req, zaehler_id, test_id):
    test = get_object_or_404(Test, pk=test_id)
    profil = req.user.profil

    # letztes offene Protokoll für diesen Test/Schüler (falls du end=None verwendest)
    prot = (
        Protokoll.objects
        .filter(profil=profil, hilfe_id=test.proto_marker, end__isnull=True)
        .order_by("-start")
        .first()
    )
    if prot:
        # abbr bleibt True, wir setzen nur Endzeit
        prot.end = timezone.now()
        prot.save()

    return redirect("test_anzeigen", test_id=test.id, profil_id=profil.id)

def loesung(req, zaehler_id, protokoll_id):
    prot = get_object_or_404(Protokoll, pk=protokoll_id)
    test_id = req.GET.get("test")
    # Test holen, damit wir später wieder wissen, wohin
    test = get_object_or_404(Test, pk=test_id)
    # Lösung markieren
    prot.lsg = True
    prot.abbr = False
    prot.end = prot.end or timezone.now()
    prot.save()
    kategorie = prot.kategorie
    # passendes Formular wie im test()-View
    if "tab" in prot.parameter.get("name", ""):
        if "term" in prot.parameter.get("name", ""):
            form = AufgabeFormTerm()
        else:
            form = AufgabeFormTab()
    else:
        form = AufgabeFormZahl() if prot.wert else AufgabeFormStr()
    try:
        if isinstance(prot.loesung[0], list):
            text = "; ".join(prot.loesung[0]).replace(".",",")
        else:
            text = prot.loesung[0]
    except:
        text = prot.loesung
    messages.info(req, f'Lösung: {text}')
    if prot.kategorie.zeile == 33 and prot.typ == 12:
        text = prot.pro_text
    else:
        text = prot.text 
    context = {
        "zaehler_id": zaehler_id,
        "protokoll_id": prot.id,
        "test_id": test.id,
        "kategorie": kategorie,
        "titel": prot.titel,
        "aufgnr": prot.aufgnr,
        "soll": None,  # im Test kannst du ggf. noch die Soll-Anzahl holen, ist hier optional
        "text": prot.text,
        "frage": prot.frage,
        "einheit": prot.einheit,
        "parameter": prot.parameter,
        "form": form,
        "message_unten": prot.anmerkung,
        "lsg": True,                      # ← wichtig, damit das Template die Lösung anzeigt
        "eingabe": prot.eingabe,
        "hinweis": "Lösung",
    }
    return render(req, "tests/test_aufgabe.html", context)

def protokoll_bewertung(req, protokoll_id):
    prot = get_object_or_404(Protokoll, pk=protokoll_id)
    # Test zu diesem Protokoll finden (über proto_marker)
    test = Test.objects.filter(proto_marker=prot.hilfe_id).first()
    if not test:
        return HttpResponseForbidden("Kein zugehöriger Test gefunden.")
    gruppe = test.gruppe
    user = req.user
    # Nur zuständige Lehrkraft dieser Gruppe oder Superuser
    if not (user.is_superuser or user == gruppe.lehrer):
        return HttpResponseForbidden("Keine Berechtigung.")
    if req.method == "POST":
        form = ProtokollBewertungForm(req.POST, instance=prot)
        if form.is_valid():
            # Werte übernehmen
            obj = form.save(commit=False)
            # negative Werte verhindern
            if obj.richtig < 0 or obj.falsch < 0:
                messages.error(req, "richtig/falsch dürfen nicht negativ sein.")
            else:
                obj.korrigiert = True
                obj.save()
                messages.success(req, "Bewertung wurde gespeichert.")
                return redirect("test_anzeigen", test_id=test.id, profil_id=prot.profil_id)
    else:
        form = ProtokollBewertungForm(instance=prot)
    context = {
        "protokoll": prot,
        "form": form,
        "test": test,
        "gruppe": gruppe,
    }
    return render(req, "tests/protokoll_bewertung.html", context)

