from django.shortcuts import redirect

class PlatformSwitchMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host()
        
        if 'physik' in host or request.path.startswith('/physik/'):
            request.platform = 'physik'
            request.login_url = '/physik/anmelden/'
            
            # Wenn die Physik-Domain aufgerufen wird und man auf der Wurzel ("/") ist,
            # direkt auf die Physik-Startseite weiterleiten:
            if request.path == '/':
                return redirect('/physik/')
        else:
            request.platform = 'mathe'
            request.login_url = '/anmelden/'
            
        response = self.get_response(request)
        return response