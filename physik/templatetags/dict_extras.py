from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    if not dictionary:
        return None
    # Erst normal versuchen (z.B. mit Integer-ID)
    res = dictionary.get(key)
    # Wenn nichts gefunden, als String versuchen
    if res is None:
        res = dictionary.get(str(key))
    return res
