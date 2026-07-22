from django import template

register = template.Library()

@register.filter
def name_kuerzen(full_name, n=1):
    """
    Zerlegt einen Namen in alle Bestandteile und nimmt von jedem Teil die ersten n Buchstaben.
    Beispiel: "Anne-Marie von der Heide" mit n=1 -> "A. v. d. H."
    """
    if not full_name:
        return ""
    
    parts = full_name.split()
    initials = [p[:n] + "." for p in parts]
    return " ".join(initials)