from django.contrib import admin
from .models import  Kategorie, Auswahl, Protokoll, Zaehler, Hilfe, Sachaufgabe, Duell_Protokoll

class AuswahlInline(admin.TabularInline):
    model = Auswahl
    extra = 0

class KategorieAdmin(admin.ModelAdmin):
    ordering = ["-zeile"]
    fieldsets = [
        (None,   {'fields': ['name', 'zeile', 'farbe', 'start_jg', 'start_sw']}),
                ('weitere Infos', {'fields': ['eof'], 'classes': ['collapse']}),        
    ]
    inlines = [AuswahlInline]
    
class ZaehlerAdmin(admin.ModelAdmin):
    search_fields = ['user__vorname', 'user__nachname']
    list_filter=("user","kategorie",)
    ordering = ["-id", "user__vorname", "kategorie__zeile"]

class ProtokollAdmin(admin.ModelAdmin):
    search_fields = ['user__vorname', 'user__nachname']
    list_filter=( "start","kategorie", "user",)
    
    list_display = ('id', 'start', 'kategorie', 'name') 
    # ordering = ["user__vorname", "kategorie__zeile"]

  
class HilfeAdmin(admin.ModelAdmin):
    list_filter=("kategorie", "hilfe_id")

admin.site.register(Sachaufgabe)

admin.site.register(Kategorie, KategorieAdmin)
admin.site.register(Hilfe, HilfeAdmin)
admin.site.register(Protokoll, ProtokollAdmin)
admin.site.register(Zaehler, ZaehlerAdmin)

admin.site.register(Duell_Protokoll)


