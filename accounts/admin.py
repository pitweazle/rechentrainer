from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from .models import   Ort, Schule, Profil, Lerngruppe, Geloescht

class OrtAdmin(admin.ModelAdmin):
    ordering = ['plz',]

class SchuleAdmin(admin.ModelAdmin):
    list_filter=("ort",)
    ordering = ['ort__plz',]

class LerngruppeAdmin(admin.ModelAdmin):
    list_filter=(
        ("lehrer", admin.RelatedOnlyFieldListFilter), 
    )

class ProfilAdmin(admin.ModelAdmin):
    list_filter=('gruppe',  )
    search_fields = ['vorname', 'nachname']
    list_display = ('vorname', 'nachname', 'klasse', 'gruppe') 

class BenutzerAdmin(UserAdmin):
    list_display = ('id', 'username', 'profil_nachname', 'profil_vorname', 'profil_gruppe', 'date_joined', 'last_login')
    ordering = ['-date_joined',]
    list_filter = ['groups', 'gruppe']
    
    def profil_vorname(self, obj):
        return obj.profil.vorname
    profil_vorname.short_description = "Vorname"

    def profil_nachname(self, obj):
        return obj.profil.nachname
    profil_nachname.short_description = "Nachname"

    def profil_gruppe(self, obj):
        return obj.profil.gruppe
    profil_nachname.short_description = "Lerngruppe"

admin.site.unregister(User)
admin.site.register(User,  BenutzerAdmin)  
admin.site.register(Ort, OrtAdmin)
admin.site.register(Schule, SchuleAdmin)
admin.site.register(Profil, ProfilAdmin)
admin.site.register(Lerngruppe, LerngruppeAdmin)
admin.site.register(Geloescht)
