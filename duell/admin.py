from django.contrib import admin
from .models import  Duellant, Duell, Duell_Protokoll

class DuellantAdmin(admin.ModelAdmin):
    list_filter=("gruppe",)

class DuellAdmin(admin.ModelAdmin):
    list_filter=("gruppe",)

class Duell_ProtokollAdmin(admin.ModelAdmin):
    list_filter=("duell__gruppe",)

admin.site.register(Duellant, DuellantAdmin)
admin.site.register(Duell, DuellAdmin)
admin.site.register(Duell_Protokoll, Duell_ProtokollAdmin)
