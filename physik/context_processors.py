from django.urls import reverse


def home_url(request):
    """
    Stellt in JEDEM Template automatisch die Variable 'home_url' zur Verfügung,
    basierend auf dem aktuellen URL-Pfad - unabhängig von Session/Login.

    - Läuft die Anfrage unter /physik/... -> Home-Link zeigt auf physik:index
    - Sonst -> kein home_url gesetzt, auswahl.html fällt auf {% url 'index' %} zurück
    """
    if request.path.startswith('/physik/'):
        return {'home_url': reverse('physik:index')}
    return {}