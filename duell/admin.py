from django.contrib import admin
from .models import  Duellant, Duell_Protokoll, Duell_Wertung

admin.site.register(Duellant)
admin.site.register(Duell_Protokoll)
admin.site.register(Duell_Wertung)
