from decimal import Decimal
from collections import defaultdict

from django.contrib import messages
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.db.models import Sum, Case, When, IntegerField

from core.models import Protokoll

from .forms import ProtokollBewertungForm
from .models import Test, TestEinstellung

def kurs_to_stufe(kurs: str) -> int:
    if kurs in ("Y", "R", "E", "A", "B"):
        return 2
    if kurs in ("H", "G", "C"):
        return 1
    return 0  # S oder i

def berechne_note(prozent, streng):
    """
    prozent: float, z.B. 83.5
    streng: bool (True = 95/80/65/50/25, False = 90/75/60/45/30)
    """
    if streng:
        grenzen = {1: 95, 2: 80, 3: 65, 4: 50, 5: 25, 6: 0}
    else:
        grenzen = {1: 90, 2: 75, 3: 60, 4: 45, 5: 30, 6: 0}
    p = float(prozent)
    # Grundnote bestimmen
    for n in range(1, 6):
        if p >= grenzen[n]:
            note = n
            break
    else:
        note = 6
    # + / - nur bei 2–5
    zusatz = ""
    if 2 <= note <= 5:
        g_akt = grenzen[note]
        g_besser = grenzen[note - 1]  # Grenze der besseren Note
        # knapp über der eigenen Grenze → Minus
        if p < g_akt + 3:
            zusatz = "-"
        # knapp unter der besseren Grenze → Plus
        elif p >= g_besser - 3:
            zusatz = "+"
    return note, zusatz

def slots_pro_tabelle(kategorie):
    """
    Wie viele 'Einzelaufgaben' zählen wir für EINE erzeugte Aufgabe dieser Kategorie?
    - Normale Aufgaben: 1
    - Wertetabellen: Anzahl relevanter Felder (z.B. 4 oder 5)
    """
    if kategorie.slug == "zuordnungen":
        return 3
    elif kategorie.slug == "terme":
        return 5
    elif kategorie.slug == "funktionen":
        return 5
    elif kategorie.slug == "quadratische-funktionen":
        return 4
    return 1

def werte_aus_wertung(wertung: str):
    """
    Wertet den String 'wertung' eines Protokolls aus.

    - zählt nur die Zeichen r/f/x (alles andere wird ignoriert: '/', Leerzeichen, Ziffern ...)
    - r_slots = Anzahl richtiger Slots (1 Punkt pro Slot)
    - f_slots = Anzahl falscher Slots
    - x_slots = Anzahl Extrapunkte-Slots (0,5 Punkt pro x)
    """
    if not wertung:
        return 0, 0, 0

    # alles klein, nur r/f/x behalten
    w = "".join(ch for ch in wertung.lower() if ch in ("r", "f", "x"))

    r_slots = w.count("r")
    f_slots = w.count("f")
    x_slots = w.count("x")
    return r_slots, f_slots, x_slots

def build_soll_map(einstellungen):
    """
    Liefert:
      soll_map: {kat.id: soll_slots}
      total_soll: Summe aller Soll-Slots im Test
    """
    soll_map = {}
    total = 0

    for e in einstellungen:
        slots_first = slots_pro_tabelle(e.kategorie)
        anzahl = e.anzahl or 0

        if anzahl <= 0:
            soll = 0
        elif anzahl == 1:
            soll = slots_first
        else:
            soll = slots_first + (anzahl - 1)

        soll_map[e.kategorie.id] = soll
        total += soll

    return soll_map, total

def analyse_protokolle(protos, soll_map):
    """
    protos = QuerySet von Protokoll-Objekten eines Schülers
    soll_map = {kat.id: soll_slots}

    Rückgabe: dict mit Slot-Zahlen & Zusammenfassung
    """

    done = defaultdict(lambda: {"r": 0, "f": 0})
    abbr = 0
    lsg = 0

    for p in protos:
        w = p.wertung or ""

        if p.abbr:
            abbr += 1
        if p.lsg:
            lsg += 1

        r = w.count("r")
        f = w.count("f")

        done[p.kategorie_id]["r"] += r
        done[p.kategorie_id]["f"] += f

    # Gesamt-Slots
    sum_r = sum(v["r"] for v in done.values())
    sum_f = sum(v["f"] for v in done.values())
    sum_erledigt = sum_r + sum_f

    # offene Slots
    total_soll = sum(soll_map.values())
    offen = max(total_soll - sum_erledigt, 0)

    return {
        "pro_kat": done,
        "r_sum": sum_r,
        "f_sum": sum_f,
        "erledigt_sum": sum_erledigt,
        "abbr": abbr,
        "lsg": lsg,
        "offen": offen,
        "total_soll": total_soll,
    }

def berechne_quote_und_note(analysis, protos, test):
    """
    analysis: dict aus analyse_protokolle()
    protos:   QuerySet[Protokoll]
    test:     Test-Objekt

    Oben (Aufgaben-Übersicht): basiert auf analysis (Slots aus 'wertung').
    Unten (Punkte/Quote/Note): basiert auf p.richtig/p.falsch + Abbr/Lsg + Cheats.
    """

    # Slot-basierte Größen aus wertung
    f_slots = Decimal(analysis["f_sum"])
    abbr = Decimal(analysis["abbr"])
    lsg = Decimal(analysis["lsg"])
    total_soll = Decimal(analysis["total_soll"])

    # Punkte aus Protokollfeldern (inkl. manueller Korrekturen)
    agg = protos.aggregate(
        richtig_sum=Sum(
            Case(
                When(richtig=True, then=1),
                default=0,
                output_field=IntegerField(),
            )
        ),
        falsch_sum=Sum(
            Case(
                When(falsch=True, then=1),
                default=0,
                output_field=IntegerField(),
            )
        ),
    )
    richtig_punkte = Decimal(agg["richtig_sum"] or 0)
    falsch_sum = Decimal(agg["falsch_sum"] or 0)

    # Cheat-Punkte: zusätzliche Fehler gegenüber den "normalen" Slot-Fehlern
    cheat_punkte = Decimal("-0.5") * (falsch_sum - f_slots)

    abbr_punkte = Decimal("0.5") * abbr
    lsg_punkte = Decimal("0.5") * lsg

    malus_punkte = abbr_punkte + lsg_punkte + cheat_punkte

    if total_soll > 0:
        pn = richtig_punkte - malus_punkte
        if pn < 0:
            pn = Decimal("0")
        quote = float((pn * Decimal("100")) / total_soll)
        quote = max(0.0, min(round(quote, 1), 100.0))
    else:
        quote = 0.0

    # Note nur, wenn Test nicht aktiv ist und überhaupt Protokolle existieren
    if (not test.aktiv) and protos.exists():
        note_zahl, zusatz = berechne_note(quote, test.note_streng)
        note = f"{note_zahl}{zusatz}"
    else:
        note = None

    return {
        "quote": quote,
        "note": note,
        "richtig_punkte": float(richtig_punkte),
        "cheat_punkte": float(cheat_punkte),
        "abbr_punkte": float(abbr_punkte),
        "lsg_punkte": float(lsg_punkte),
    }
