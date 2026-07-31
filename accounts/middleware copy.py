class PlatformSwitchMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host()
        
        if 'physik' in host or request.path.startswith('/physik/'):
            request.platform = 'physik'
            # Setze die Login-URL dynamisch für den Physiktrainer
            request.login_url = '/physik/anmelden/'
        else:
            request.platform = 'mathe'
            # Setze die Login-URL für den Rechentrainer (passe den Pfad an, falls er anders heißt)
            request.login_url = '/anmelden/'  # oder wie immer der Mathe-Login heißt
            
        response = self.get_response(request)
        return response