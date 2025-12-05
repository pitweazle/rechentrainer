from django import template
from ..utilities import slots_pro_tabelle

register = template.Library()

@register.filter
def kuerze_lsg(protokoll):
    """
    Gibt die Lösungsliste gekürzt auf die tatsächliche Slot-Anzahl zurück.
    Für Wertetabellen wird der Zufalls-/Extra-Wert am Ende entfernt.
    Rückgabe ist ein hübscher String, z.B. "3; 8; 15; 0".
    """
    if protokoll is None:
        return ""

    lsg = getattr(protokoll, "loesung", None)

    if not isinstance(lsg, (list, tuple)) or not lsg:
        return lsg

    # Viele deiner Tabellen haben Struktur: [ [werte...], ... ]
    if isinstance(lsg[0], (list, tuple)):
        werte = list(lsg[0])
    else:
        werte = list(lsg)

    slots = slots_pro_tabelle(protokoll.kategorie)  # 1,3,4,5 je nach Kat
    werte = werte[:slots]

    # Als String zurückgeben
    return "; ".join(str(v) for v in werte)
