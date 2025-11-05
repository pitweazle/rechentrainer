from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from .models import   Ort, Schule, Profil, Lerngruppe, Geloescht

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
    list_filter=("ort",)
    ordering = ['ort__plz',]

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
        return getattr(obj.profil, 'vorname', '')  # failsafe
    profil_vorname.short_description = "Vorname"

    def profil_nachname(self, obj):
        return getattr(obj.profil, 'nachname', '')
    profil_nachname.short_description = "Nachname"

    def profil_gruppe(self, obj):
        return getattr(obj.profil, 'gruppe', None)
    profil_gruppe.short_description = "Lerngruppe"   # ⚠️ hier war zuvor ein Tippfehler


class GeloeschtAdmin(admin.ModelAdmin):
    search_fields = ['benutzername']

admin.site.unregister(User)
admin.site.register(User,  BenutzerAdmin)  
admin.site.register(Ort, OrtAdmin)
admin.site.register(Schule, SchuleAdmin)
admin.site.register(Profil, ProfilAdmin)
admin.site.register(Lerngruppe, LerngruppeAdmin)
admin.site.register(Geloescht, GeloeschtAdmin)
