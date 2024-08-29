from django.contrib import admin
from .models import  Duellant, Duell, Duell_Protokoll

admin.site.register(Duellant)
admin.site.register(Duell)
admin.site.register(Duell_Protokoll)
