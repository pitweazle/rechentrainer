from django.contrib import admin
from .models import  Kategorie, Auswahl, Protokoll, Zaehler, Hilfe, Sachaufgabe

class AuswahlInline(admin.TabularInline):
    model = Auswahl
    extra = 0

class KategorieAdmin(admin.ModelAdmin):
    ordering = ["-zeile"]
    fieldsets = [
        (None,   {'fields': ['name', 'zeile', 'farbe', 'start_jg', 'start_sw']}),
                ('weitere Infos', {'fields': ['eof', 'geloeschte_aufgaben'], 'classes': ['collapse']}),        
    ]
    inlines = [AuswahlInline]
    
class ZaehlerAdmin(admin.ModelAdmin):
    readonly_fields = ["fehler_ab"]
    search_fields = ['profil__vorname', 'profil__nachname']
    list_filter=("profil","kategorie",)
    ordering = ["-id", "profil__vorname", "kategorie__zeile"]

class ProtokollAdmin(admin.ModelAdmin):
    search_fields = ['profil__vorname', 'profil__nachname', 'id']
    list_filter=( "start","kategorie", "profil__gruppe",)
    
    list_display = ('id', 'start', 'kategorie', 'name') 
    # ordering = ["user__vorname", "kategorie__zeile"]
  
class HilfeAdmin(admin.ModelAdmin):
    list_filter=("kategorie", "hilfe_id")

admin.site.register(Sachaufgabe)

admin.site.register(Kategorie, KategorieAdmin)
admin.site.register(Hilfe, HilfeAdmin)

admin.site.register(Zaehler, ZaehlerAdmin)
admin.site.register(Protokoll, ProtokollAdmin)




