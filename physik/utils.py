"""
Hilfsfunktionen für den Physiktrainer
"""


def typ_zu_klartext(typ, loesung, optionen):
    """
    Wandelt den Typ einer Aufgabe (z. B. "1u(2o3)") in Klartext um.
    
    Args:
        typ (str): Der Typ der Aufgabe (z. B. "1u(2o3)")
        loesung (str): Die Lösung der Aufgabe
        optionen (list): Liste der Optionen (mit position und text)
    
    Returns:
        str: Klartext-Darstellung des Typs (z. B. "'Lösung' UND ('Option 2' ODER 'Option 3')")
    """
    if not typ:
        return "Kein Typ angegeben."

    klartext = typ

    # Ersetze Operatoren
    klartext = klartext.replace("u", " UND ").replace("o", " ODER ")
    klartext = klartext.replace("f", " ABER NICHT ")
    klartext = klartext.replace("Y", "").replace("Z", "")

    # Index 1 = Lösung
    klartext = klartext.replace("1", f"'{loesung}'")

    # Erstelle Mapping: Position in DB -> Text
    position_to_text = {opt.position: opt.text for opt in optionen}

    # Ersetze die Zahlen im Typ durch die Texte
    for position, text in position_to_text.items():
        klartext = klartext.replace(str(position), f"'{text}'")

    # Aufräumen
    klartext = " ".join(klartext.split())

    return klartext
