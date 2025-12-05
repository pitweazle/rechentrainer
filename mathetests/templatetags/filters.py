from django import template
from ..utilities import slots_pro_tabelle

register = template.Library()

@register.filter
def kuerze_lsg(protokoll):
    """
    Gibt die im Protokoll gespeicherte Lösung passend formatiert zurück.

    - Normalfall (keine Wertetabelle):
        loesung = [irgendwas, ...]
        → es wird NUR der erste Eintrag angezeigt.

    - Wertetabellen (slots_pro_tabelle > 1 UND loesung[0] ist Liste):
        loesung = [[w1, w2, w3, ..., extra]]
        → es wird die innere Liste OHNE den letzten Eintrag angezeigt:
          "w1; w2; w3; ..."
    """
    if protokoll is None:
        return ""

    lsg = getattr(protokoll, "loesung", None)
    if not isinstance(lsg, (list, tuple)) or not lsg:
        return ""

    first = lsg[0]

    # Wertetabelle erkennen: mehr als 1 Slot und erste Lösung ist Liste
    slots = slots_pro_tabelle(protokoll.kategorie)

    if slots > 1 and isinstance(first, (list, tuple)):
        werte = list(first)

        # Falls mehr Werte als Slots: auf Slot-Anzahl kürzen
        if len(werte) > slots:
            werte = werte[:slots]
        # Falls gleich viele oder weniger: einfach so nehmen
        return "; ".join(str(v) for v in werte)

    # Normalfall: einfach den ersten Eintrag der Liste anzeigen
    return str(first)
