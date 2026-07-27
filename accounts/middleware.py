class PlatformSwitchMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host()
        
        # Hier schaut die Middleware, woher der Request kommt:
        # Entweder das Wort "physik" steht in der URL/Domain, 
        # oder der Pfad beginnt mit /physik/
        if 'physik' in host or request.path.startswith('/physik/'):
            request.platform = 'physik'
        else:
            request.platform = 'mathe'
            
        response = self.get_response(request)
        return response