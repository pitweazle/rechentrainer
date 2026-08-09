from difflib import SequenceMatcher
import re
from .models import Protokoll, FehlerLog
import requests
import os
from dotenv import load_dotenv

load_dotenv()

# ===========================================================
# VERGLEICHE (Kern-Logik für Sätze)
# ===========================================================

def vergleich_streng(index, aufgabe, antwort_norm, antwort_original, case_sensitiv, contain):
    # Feld-Zuordnung: 1 = loesung, ab 2 = optionen
    if index == 1:
        text = aufgabe.loesung
    else:
        opts = list(aufgabe.optionen.order_by("position"))
        pos = index - 2
        if pos < 0 or pos >= len(opts):
            return False, None
        text = opts[pos].text

    if not text:
        return False, None

    # Normalisierung für den Vergleich
    soll = text.strip()
    ist = antwort_original.strip()

    if not case_sensitiv:
        soll = soll.casefold()
        ist = ist.casefold()

    # Logik: Teilstring-Suche (für Sätze) oder exakter Vergleich
    if contain:
        # Prüft, ob das Wort/Phrase irgendwo im Satz vorkommt
        return (soll in ist), None
    else:
        # Entfernt Leerzeichen für absolut exakten Check (z.B. bei Zahlen/Formeln)
        soll_clean = "".join(soll.split())
        ist_clean = "".join(ist.split())
        return (soll_clean == ist_clean), None

def vergleich_fuzzy(index, aufgabe, antwort_norm, antwort_original, ratio):
    if index == 1:
        text = aufgabe.loesung
    else:
        opts = list(aufgabe.optionen.order_by("position"))
        text = opts[index-2].text if (index-2) < len(opts) else ""

    if not text or not antwort_original:
        return False, None

    soll = text.casefold().strip()
    ist_satz = antwort_original.casefold().strip()

    # 1. Schneller Check: Ist das Wort exakt im Satz?
    if soll in ist_satz:
        return True, None

    # 2. Wort-für-Wort Fuzzy Check (Damit Tippfehler in langen Sätzen erkannt werden)
    woerter_im_satz = re.findall(r'\w+', ist_satz)

    for wort in woerter_im_satz:
        if SequenceMatcher(None, soll, wort).ratio() >= ratio:
            return True, f"Fast richtig – gemeint war: {text}"

    return False, None

# # NEUE FUNKTION: Vergleich mit Mistral-API für logische Ausdrücke (o/u)
def bewerte_aufgabe(request, aufgabe, user_antwort, text_antwort=None, bild_antwort=None, session=None):
    ergebnis = None
    typ_roh = (aufgabe.typ or "").strip()

    # Fallback für Tests
    if not text_antwort and user_antwort:
        text_antwort = user_antwort

    norm = "".join(text_antwort.split()) if text_antwort else ""

    # Flags bereinigen
    typ_rein = typ_roh.replace("X", "").replace("Y", "").replace("Z", "").strip()

    # WICHTIG: Erkennung ob logischer Ausdruck (o/u) oder reine Zahl
    ist_logisch = 'o' in typ_rein or 'u' in typ_rein
    is_pure_number = typ_rein.isdigit()

    # X-Flag: Case Sensitivity
    if is_pure_number:
        case_sensitiv = ("X" not in typ_roh)
    else:
        case_sensitiv = ("X" in typ_roh)

    # Fuzzy-Aktivierung (Y, Z oder automatisch bei o/u)
    fuzzy_aktiv = False
    ratio = 0.8
    if "Y" in typ_roh:
        fuzzy_aktiv = True
        ratio = 0.8
    elif "Z" in typ_roh:
        fuzzy_aktiv = True
        ratio = 0.65
    elif ist_logisch:
        # Für logische Ausdrücke nutzen wir die API
        fuzzy_aktiv = False  # API ersetzt Fuzzy

    typ = typ_rein

    # --- A. Spezial-Typen (r, p, w, a, e) ---
    if typ == "r":
        ergebnis = bewerte_rechnen(aufgabe, text_antwort, request)
    elif "p" in typ:
        ergebnis = bewerte_bildauswahl(aufgabe, bild_antwort, session)
    elif "w" in typ:
        ergebnis = bewerte_wahr_falsch(aufgabe, norm)
    elif "a" in typ:
        ergebnis = bewerte_liste(aufgabe, text_antwort)
    elif "l" in typ:
        ergebnis = bewerte_luecke(aufgabe, user_antwort, fuzzy_aktiv, ratio)

    # --- B. Text-Parser (Der entscheidende Teil) ---
    if not ergebnis and "f" in typ:
        ok, hinweis = pruefe_verbotene_begriffe(aufgabe, norm, text_antwort)
        if not ok:
            ergebnis = {"richtig": False, "hinweis": hinweis}

    # 1. Reiner Zahlentyp (nur eine Ziffer)
    if not ergebnis and is_pure_number:
        idx = int(typ)
        ok, _ = vergleich_streng(idx, aufgabe, norm, text_antwort, case_sensitiv, False)
        if ok:
            ergebnis = {"richtig": True, "hinweis": "Richtig!"}
        elif fuzzy_aktiv:
            ok_f, f_hinw = vergleich_fuzzy(idx, aufgabe, norm, text_antwort, ratio)
            if ok_f:
                ergebnis = {"richtig": True, "hinweis": f_hinw or "Richtig!"}

    # 2. Logische Ausdrücke (1o2, 1u(2o3) etc.)
    if not ergebnis and ist_logisch:
        # NUTZE API FÜR LOGISCHE AUSDRÜCKE
        streng_ok, hinweis = bewerte_booleschen_ausdruck(
            typ, aufgabe, norm, text_antwort, ist_logisch,
            lambda idx, aufg, n, o: vergleich_fuzzy(idx, aufg, n, o, 0.8)
        )
        if streng_ok:
            ergebnis = {"richtig": True, "hinweis": "Richtig!"}
        else:
            # Falls API "stimmt nicht" zurückgibt, versuche Fuzzy als Fallback
            if fuzzy_aktiv:
                fuzzy_ok, f_hinw = bewerte_booleschen_ausdruck(
                    typ, aufgabe, norm, text_antwort, ist_logisch,
                    lambda idx, aufg, n, o: vergleich_fuzzy(idx, aufg, n, o, ratio)
                )
                if fuzzy_ok:
                    ergebnis = {"richtig": True, "hinweis": f_hinw or "Fast richtig!"}

    # --- C. Protokollierung & FehlerLog (Bleibt gleich) ---
    if ergebnis is None:
        ergebnis = {"richtig": False, "hinweis": "Leider falsch."}

    if not ergebnis.get("richtig") and text_antwort:
        FehlerLog.objects.get_or_create(
            aufgabe=aufgabe,
            eingegebene_antwort=text_antwort.strip()
        )

    return ergebnis

# ===========================================================
# PARSER
# ===========================================================
def bewerte_booleschen_ausdruck(typ, aufgabe, antwort_norm, antwort_original, ist_logisch, vergleich):
    tokens = []
    i = 0
    while i < len(typ):
        if typ[i].isdigit():
            j = i
            while j < len(typ) and typ[j].isdigit():
                j += 1
            tokens.append(("NUM", int(typ[i:j])))
            i = j
        elif typ[i] in "ou()":
            tokens.append((typ[i], typ[i]))
            i += 1
        else:
            i += 1

    pos = 0

    def peek():
        return tokens[pos] if pos < len(tokens) else None

    def eat(k):
        nonlocal pos
        if peek() and peek()[0] == k:
            pos += 1
            return True
        return False

    def expr():
        res_ok, res_hinweis = term()
        while peek() and peek()[0] == "o":
            eat("o")
            ok2, hinw2 = term()
            res_ok = res_ok or ok2
            if ok2 and not res_hinweis:
                res_hinweis = hinw2
        return res_ok, res_hinweis

    def term():
        res_ok, res_hinweis = factor()
        while peek() and peek()[0] == "u":
            eat("u")
            ok2, hinw2 = factor()
            res_ok = res_ok and ok2
            if not ok2: res_hinweis = hinw2
        return res_ok, res_hinweis

    def factor():
        nonlocal pos
        tok = peek()
        if not tok: return False, None

        if tok[0] == "(":
            eat("(")
            res = expr()
            eat(")")
            return res

        if tok[0] == "NUM":
            num1 = tok[1]
            eat("NUM")

            # PRÜFUNG: Folgt ein 'o' und eine weitere NUM? (Bereichs-Check)
            if peek() and peek()[0] == "o":
                if pos + 1 < len(tokens) and tokens[pos+1][0] == "NUM":
                    eat("o") # 'o' essen
                    num2 = tokens[pos][1]
                    eat("NUM") # zweite Zahl essen

                    for n in range(num1, num2 + 1):
                        ok, hinw = vergleich(n, aufgabe, antwort_norm, antwort_original)
                        if ok: return True, hinw
                    return False, None

            # Normalfall: Einzelvergleich
            return vergleich(num1, aufgabe, antwort_norm, antwort_original)

        return False, None
    return expr()

# ===========================================================
# HILFSFUNKTIONEN (unverändert)
# ===========================================================

def normalisiere(text):
    return "".join(text.split()) if text else ""

def bewerte_rechnen(aufgabe, antwort, request):
    idx = request.session.get('aktiver_index', 0)
    loesungs_liste = [l.strip() for l in aufgabe.loesung.split(";")]

    try:
        korrektes_ergebnis = loesungs_liste[idx]
    except:
        korrektes_ergebnis = loesungs_liste[0]

    import re
    ist_clean = re.sub(r'[^0-9,.]', '', antwort).replace(",", ".")
    soll_clean = re.sub(r'[^0-9,.]', '', korrektes_ergebnis).replace(",", ".")

    if ist_clean == soll_clean and ist_clean != "":
        return {"richtig": True, "hinweis": "Richtig gerechnet!"}

    return {
        "richtig": False,
        "hinweis": (
            f"Das Ergebnis ist leider nicht korrekt.<br><br>"
            f"<strong>Deine Eingabe:</strong> »{antwort}«<br>"
            f"<strong>Richtig wäre:</strong> »{korrektes_ergebnis}«"
        )
    }

def bewerte_bildauswahl(aufgabe, bild_antwort, session):
    ist_richtig = session and str(session.get("p_richtig")) == str(bild_antwort)
    return {
        "richtig": ist_richtig,
        "hinweis": "Richtig!" if ist_richtig else "Leider falsch.",
        "ungueltig": False
    }

def bewerte_wahr_falsch(aufgabe, norm):
    t = (norm or "").lower()
    db_lsg = "".join((aufgabe.loesung or "").lower().split()).rstrip(".")

    WAHR_GRUPPE = {"w", "wahr", "ja", "j", "richtig", "r", "ok", "stimmt"}
    FALSCH_GRUPPE = {"f", "falsch", "nein", "n", "stimmtnicht"}

    user_meint_wahr = t in WAHR_GRUPPE
    user_meint_falsch = t in FALSCH_GRUPPE

    db_ist_wahr = db_lsg in WAHR_GRUPPE
    db_ist_falsch = db_lsg in FALSCH_GRUPPE

    if user_meint_wahr:
        return {"richtig": db_ist_wahr, "hinweis": "Richtig!" if db_ist_wahr else "Leider falsch."}
    if user_meint_falsch:
        return {"richtig": db_ist_falsch, "hinweis": "Richtig!" if db_ist_falsch else "Leider falsch."}

    return {
        "richtig": False,
        "ungueltig": True,
        "hinweis": "Bitte mit w/f, wahr/falsch oder ja/nein antworten."
    }

def bewerte_liste(aufgabe, antwort):
    korrekt_text = aufgabe.loesung
    gewaehlter_text = ""

    try:
        idx = int(antwort)
        if idx == 0:
            return {"richtig": True, "hinweis": "Richtig!"}
        else:
            opts = list(aufgabe.optionen.order_by("position"))
            pos = idx - 1
            if 0 <= pos < len(opts):
                gewaehlter_text = opts[pos].text
    except (ValueError, TypeError):
        gewaehlter_text = antwort
        if normalisiere(antwort) == normalisiere(korrekt_text):
            return {"richtig": True, "hinweis": "Richtig!"}

    wahl_display = f"»{gewaehlter_text}«" if gewaehlter_text else f"Nummer {antwort}"
    return {
        "richtig": False,
        "hinweis": (
            f"Das war leider nicht die gesuchte Antwort.<br><br>"
            f"**Deine Wahl:** {wahl_display}<br>"
            f"**Richtig wäre:** »{korrekt_text}«"
        )
    }

def bewerte_e_typ(typ, aufgabe, antwort, case_sensitiv, is_integer, ratio, fuzzy_aktiv):
    links, rechts = typ.split("e", 1)
    teile = re.split(r';|\.\.\.', antwort)

    if len(teile) >= 2:
        a = teile[0].strip()
        b = teile[1].strip()
    else:
        return False, "Bitte zwei Begriffe mit ';' oder '...' trennen."

    norm_a = normalisiere(a)
    norm_b = normalisiere(b)

    def check_einzeln(t_typ, n_val, o_val):
        ok, _ = bewerte_booleschen_ausdruck(t_typ, aufgabe, n_val, o_val, False,
                    lambda idx, aufg, n, o: vergleich_streng(idx, aufg, n, o, case_sensitiv, not is_integer))
        if ok:
            return True, None
        if fuzzy_aktiv:
            ok_f, hinw_f = bewerte_booleschen_ausdruck(t_typ, aufgabe, n_val, o_val, False,
                                lambda idx, aufg, n, o: vergleich_fuzzy(idx, aufg, n, o, ratio))
            if ok_f:
                return True, hinw_f
        return False, None

    ok1, hinweis1 = check_einzeln(links, norm_a, a)
    ok2, hinweis2 = check_einzeln(rechts, norm_b, b)

    if ok1 and ok2:
        h = "Richtig!"
        if hinweis1 or hinweis2:
            h = f"Fast richtig! (Achte auf: {hinweis1 or ''} {hinweis2 or ''})".strip()
        return True, h

    if ok1: return False, "Der erste Begriff ist richtig, der zweite ist falsch oder fehlt."
    if ok2: return False, "Der zweite Begriff ist richtig, der erste ist falsch oder fehlt."
    return False, "Beide Begriffe sind leider falsch."

def pruefe_verbotene_begriffe(aufgabe, norm, text_antwort):
    typ = (aufgabe.typ or "").strip()
    if "f" not in typ:
        return True, ""

    _, verbot = typ.split("f", 1)
    if not verbot:
        return True, ""

    kommt_vor, _ = bewerte_booleschen_ausdruck(
        verbot,
        aufgabe,
        norm,
        text_antwort,
        False,  # ist_logisch=False, da verbotene Begriffe nicht logisch sind
        lambda i, a, n, o: vergleich_streng(i, a, n, o, case_sensitiv=False, contain=True)
    )

    if not kommt_vor:
        return True, ""

    verbotener_begriff = None
    i = 0
    indices = []
    while i < len(verbot):
        if verbot[i].isdigit():
            j = i
            while j < len(verbot) and verbot[j].isdigit():
                j += 1
            indices.append(int(verbot[i:j]))
            i = j
        else:
            i += 1

    for k in indices:
        ok, _ = vergleich_streng(k, aufgabe, norm, text_antwort, case_sensitiv=False, contain=True)
        if ok:
            if k == 1:
                verbotener_begriff = aufgabe.loesung
            else:
                opts = list(aufgabe.optionen.order_by("position"))
                if k - 2 < len(opts):
                    verbotener_begriff = opts[k - 2].text
            break

    if not verbotener_begriff:
        verbotener_begriff = text_antwort

    erklaerung = getattr(aufgabe, "erklaerung", "").strip()
    if erklaerung:
        hinweis = (
            f"Das ist hier falsch: „{verbotener_begriff}“\n\n"
            f"Begründung: {erklaerung}"
        )
    else:
        hinweis = f"Das ist hier falsch: „{verbotener_begriff}“"

    return False, hinweis

def bewerte_luecke(aufgabe, user_antwort, fuzzy_aktiv=False, ratio=0.8):
    optionen = aufgabe.optionen.all().order_by('position', 'id')
    anzahl_vorgabe = optionen.count()

    user_eingaben = [a.strip() for a in user_antwort.split(";") if a.strip()]
    anzahl_user = len(user_eingaben)

    if anzahl_user != anzahl_vorgabe:
        return {
            "richtig": False,
            "hinweis": f"Die Anzahl der Begriffe stimmt nicht. Erwartet werden <b>{anzahl_vorgabe}</b> Begriffe (getrennt durch Semikolon), du hast <b>{anzahl_user}</b> eingegeben. Versuch es noch einmal!"
        }

    loesungs_vorgaben = [opt.text for opt in optionen]

    for i, korrekter_text in enumerate(loesungs_vorgaben):
        user_wort = user_eingaben[i]
        erlaubte = [e.strip() for e in str(korrekter_text).split(";") if e.strip()]

        wort_korrekt = False
        for alternative in erlaubte:
            if fuzzy_aktiv:
                u_word_lower = user_wort.lower()
                alt_lower = alternative.lower()
                similarity = SequenceMatcher(None, u_word_lower, alt_lower).ratio()
                if alt_lower in u_word_lower or similarity >= ratio:
                    wort_korrekt = True
                    break
            else:
                if user_wort == alternative:
                    wort_korrekt = True
                    break

        if not wort_korrekt:
            loesung_hilfe = " ; ".join([f"<b>{t.split(';')[0].strip()}</b>" for t in loesungs_vorgaben])
            return {
                "richtig": False,
                "hinweis": f"Nicht ganz korrekt. Die Begriffe wären: {loesung_hilfe}"
            }

    return {"richtig": True, "hinweis": "Hervorragend! Alles korrekt gelöst."}

from django.core.mail import send_mail
from django.conf import settings

def check_answer_with_api(frage, loesung, schueler_antwort, typ=None, optionen=None):
    """
    Ruft die Mistral-API auf, um eine Schülerantwort zu überprüfen.
    - Bei richtiger Antwort: Gibt "stimmt" zurück.
    - Bei falscher Antwort: Gibt eine kurze Erklärung (max. 25 Wörter) zurück.
    - Bei API-Fehlern: Sendet eine E-Mail an info@physiktrainer.app.
    
    Parameter:
    - typ: Der Typ der Aufgabe (z. B. "3u(4o5)" für logische Verknüpfungen).
    - optionen: QuerySet der Optionen (z. B. aufgabe.optionen.all()).
    """
    api_url = os.getenv("MISTRAL_API_URL")
    api_key = os.getenv("MISTRAL_API_KEY")

    if not api_url or not api_key:
        raise ValueError("API-Key oder URL fehlt in .env")

    # Optionen als String formatieren (falls vorhanden)
    optionen_text = ""
    if optionen:
        optionen_text = "\n".join([f"  {i+1}: {opt.text}" for i, opt in enumerate(optionen)])
    
    # Typ-Erklärung für die KI
    typ_hinweis = ""
    if typ:
        typ_hinweis = f"- Kriterien: {typ} (z. B. logische Verknüpfung von Optionen)"

    # NEUER PROMPT: Freie Formulierung mit Fokus auf physikalische Prinzipien
    prompt = f"""
    Ein Physiklehrer hat die Antwort **"{schueler_antwort}"** eines Schülers auf die Frage **"{frage}"** als falsch gewertet.
    Er hat dies nach den Kriterien **"{typ}"** (z. B. logische Verknüpfung von Optionen) beurteilt.

    **Möglicherweise hat der Schüler aber doch Recht!**
    Deine Aufgabe als **unabhängiger Physik-Experte**:
    - Prüfe, ob die Schülerantwort **physikalische Prinzipien korrekt anwendet** – auch wenn sie nicht offensichtlich oder wortwörtlich mit der Lösung übereinstimmt.
    - Die Antwort soll **nicht nur oberflächlich richtig sein**, sondern zeigen, dass der Schüler **physikalische Zusammenhänge verstanden hat**.

    ---
    **Kontext:**
    - **Korrekte Lösung:** {loesung}
    - **Optionen (falls vorhanden):**
    {optionen_text}

    ---
    **Bewertungskriterien:**
    1. **Physikalische Tiefe:**
       - Akzeptiere Antworten, die **physikalische Prinzipien** korrekt anwenden, auch wenn sie anders formuliert sind.
         - Beispiel: Frage: *"Warum plustern Vögel ihr Gefieder auf?"*
           - Oberflächlich: *"Damit sie nicht erfrieren."* → **Nicht akzeptieren** (fehlende Physik).
           - Korrekt: *"Mehr Luft im Gefieder isoliert und reduziert den Wärmeverlust."* → **Akzeptieren**.
       - **Synonyme sind erlaubt**, wenn sie physikalisch äquivalent sind (z. B. *"isoliert"* = *"dämmt"* = *"reduziert Wärmeübertragung"*).

    2. **Bezug zu den Optionen:**
       - Falls die Schülerantwort **Begriffe aus den Optionen** verwendet, die physikalisch korrekt sind, bewerten sie als richtig.
       - Falls die Antwort **falsche oder unpräzise Begriffe** enthält, vergleiche sie mit den Optionen und weise darauf hin.

    3. **Rückmeldung:**
       - **Falls die Antwort physikalisch korrekt ist:**
         - Antworte **nur** mit: `"stimmt"`
       - **Falls die Antwort falsch oder unvollständig ist:**
         - Gib eine **kurze, präzise Rückmeldung (max. 25 Wörter)**, die:
           1. **Den Fehler benennt** (z. B. *"Fehlt der Bezug zur Wärmeleitung."*).
           2. **Auf korrekte Begriffe hinweist** (z. B. *"Nutze Begriffe wie 'Isolierung' oder 'Wärmeverlust' (siehe Optionen)."*).
       - **Falls die Antwort oberflächlich ist:**
         - Fordere eine **physikalische Begründung** ein (z. B. *"Erkläre das Prinzip, z. B. 'Luft isoliert durch geringe Wärmeleitung'."*).

    ---
    **Wichtig:**
    - **Sei streng mit Oberflächlichkeit**, aber fair mit alternativen Formulierungen.
    - **Nutze die Optionen als Referenz** für erwartete Begriffe.
    - **Maximal 25 Wörter** in der Rückmeldung.
    """

    payload = {
        "model": "mistral-medium",
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3,
        "max_tokens": 50,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers)
        response.raise_for_status()
        result = response.json()
        answer = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()

        # Debug-Ausgabe im Terminal
        print(f"[KI-DEBUG] Frage: {frage[:50]}... | Lösung: {loesung[:20]}... | Antwort: {schueler_antwort[:20]}... | KI-Ergebnis: {answer}")

        if answer.lower() == "stimmt":
            return "stimmt"
        else:
            # Begrenze auf 25 Wörter
            woerter = answer.split()
            if len(woerter) > 25:
                answer = " ".join(woerter[:25]) + "..."
            return answer

    except requests.exceptions.HTTPError as e:
        error_msg = f"Mistral API-Fehler (HTTP {e.response.status_code}): {str(e)}"
        if e.response.status_code in [402, 429]:
            try:
                send_mail(
                    subject=f"[Physiktrainer] Mistral API-Fehler: {e.response.status_code}",
                    message=f"Fehler bei der API-Anfrage:\n\n{error_msg}\n\nFrage: {frage}\nLösung: {loesung}\nAntwort: {schueler_antwort}",
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=["info@physiktrainer.app"],
                    fail_silently=True,
                )
            except Exception:
                pass
        raise RuntimeError(error_msg)

    except requests.exceptions.RequestException as e:
        error_msg = f"Mistral API-Netzwerkfehler: {str(e)}"
        try:
            send_mail(
                subject="[Physiktrainer] Mistral API-Netzwerkfehler",
                message=f"Netzwerkfehler bei der API-Anfrage:\n\n{error_msg}",
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=["info@physiktrainer.app"],
                fail_silently=True,
            )
        except Exception:
            pass
        raise RuntimeError(error_msg)
