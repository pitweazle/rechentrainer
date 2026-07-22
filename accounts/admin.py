from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from django.core.exceptions import ObjectDoesNotExist

from .models import   Ort, Schule, Profil, Lerngruppe, Geloescht, EwigeBestenliste, LoginLog

class GruppeFilter(admin.SimpleListFilter):
    title = 'Lerngruppe'
    parameter_name = 'gruppe'
    def lookups(self, request, model_admin):
        # Passe 'name' an, falls deine Lerngruppe anders heißt
        return [(g.pk, getattr(g, 'name', str(g))) for g in Lerngruppe.objects.all()]
    def queryset(self, request, queryset):
        gid = self.value()
        if gid:
            return queryset.filter(profil__gruppe_id=gid)
        return queryset

class OrtAdmin(admin.ModelAdmin):
    ordering = ['plz',]

class SchuleAdmin(admin.ModelAdmin):
    list_display = ('id', 'schulname', 'ort', 'dienststellen_nr')
    list_display_links = ('id', 'schulname')
    list_filter = ("ort",)
    ordering = ['ort__plz',]
    search_fields = ('schulname', 'dienststellen_nr')

from .models import ExterneSchnittstelleConfig

@admin.register(ExterneSchnittstelleConfig)
class ExterneSchnittstelleConfigAdmin(admin.ModelAdmin):
    list_display = ('schulname', 'typ', 'consumer_key', 'schule')
    list_filter = ('typ', 'schule')
    search_fields = ('schulname', 'consumer_key')

    fieldsets = (
        ('Allgemeine Infos', {
            'fields': ('schulname', 'typ', 'schule')
        }),
        ('Sicherheits-Schlüssel (Credentials)', {
            'fields': ('consumer_key', 'shared_secret'),
            'description': 'Gibe diese Daten an den Moodle-Admin der Schule weiter.'
        }),
    )

class LerngruppeAdmin(admin.ModelAdmin):
    list_filter=(
        ("lehrer", admin.RelatedOnlyFieldListFilter), 
    )
    ordering = ('-id',)

class ProfilAdmin(admin.ModelAdmin):
    list_filter=('gruppe',  )
    search_fields = ['vorname', 'nachname']

    # fieldsets = [
    #     (None,   {'fields': [('vorname', 'nachname', 'klasse', 'gruppe') ]}),
    #             ('weitere Infos', {'fields': ['schuljahr_ab', 'halbjahr_ab'], 'classes': ['collapse']}),        
    # ]

    list_display = ('pk', 'vorname', 'nachname', 'klasse', 'gruppe') 

class BenutzerAdmin(UserAdmin):
    list_display = ('id', 'username', 'profil_nachname', 'profil_vorname', 'profil_gruppe', 'date_joined', 'last_login')
    ordering = ['-date_joined']
    list_filter = ('groups', GruppeFilter)   # ✅ statt 'gruppe'
    list_select_related = ('profil', 'profil__gruppe')  # Performance

    def profil_vorname(self, obj):
        try:
            return obj.profil.vorname
        except (Profil.DoesNotExist, ObjectDoesNotExist):
            return ""
    profil_vorname.short_description = "Vorname"

    def profil_nachname(self, obj):
        try:
            return obj.profil.nachname
        except (Profil.DoesNotExist, ObjectDoesNotExist):
            return ""
    profil_nachname.short_description = "Nachname"

    def profil_gruppe(self, obj):
        try:
            return obj.profil.gruppe
        except (Profil.DoesNotExist, ObjectDoesNotExist):
            return None
    profil_gruppe.short_description = "Mathegruppe"

class GeloeschtAdmin(admin.ModelAdmin):
    search_fields = ['benutzername',]
    list_filter = ['grund','benutzername',]

@admin.register(LoginLog)
class LoginLogAdmin(admin.ModelAdmin):
    list_display = ('zeitpunkt', 'consumer_key', 'user_id')
    ordering = ('-zeitpunkt',)

@admin.register(EwigeBestenliste)
class EwigeBestenlisteAdmin(admin.ModelAdmin):
    # Damit du in der Übersicht direkt sortieren kannst
    list_display = ('name', 'schule', 'lehrer', 'punkte', 'letztes_datum')
    
    # Damit du bei vielen Einträgen schnell suchen kannst
    search_fields = ('name', 'schule', 'lehrer')
    
    # Damit du direkt nach Punkten oder Datum filtern kannst
    list_filter = ('schule', 'lehrer', 'letztes_datum')
    
    # Optional: Damit die Liste automatisch absteigend nach Punkten sortiert ist
    ordering = ('-punkte',)

admin.site.unregister(User)
admin.site.register(User,  BenutzerAdmin)  
admin.site.register(Ort, OrtAdmin)
admin.site.register(Schule, SchuleAdmin)
admin.site.register(Profil, ProfilAdmin)
admin.site.register(Lerngruppe, LerngruppeAdmin)
admin.site.register(Geloescht, GeloeschtAdmin)
