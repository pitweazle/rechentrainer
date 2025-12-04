
from decimal import Decimal
from django.db.models import Sum, Case, When, IntegerField
from core.models import Protokoll
from .models import TestEinstellung

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

# mathetests/utilities.py

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
