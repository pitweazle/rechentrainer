import base64
from django.http import HttpResponse

class BasicAuthMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # Zugangsdaten
        username = "einstein"
        password = "physik"

        auth_header = request.META.get('HTTP_AUTHORIZATION')
        
        if auth_header and auth_header.startswith('Basic '):
            try:
                auth_decoded = base64.b64decode(auth_header[6:]).decode('utf-8')
                user, pwd = auth_decoded.split(':', 1)
                if user == username and pwd == password:
                    return self.get_response(request)
            except Exception:
                pass

        # Wenn nicht autorisiert, Login-Fenster erzwingen
        response = HttpResponse("Anmeldung erforderlich", status=401)
        response['WWW-Authenticate'] = 'Basic realm="Physiktrainer Login"'
        return response