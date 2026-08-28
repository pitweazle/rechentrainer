from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin

from django.core.exceptions import ObjectDoesNotExist

from .models import   Ort, Schule, Profil, Lerngruppe, Geloescht, LoginLog

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

class LerngruppeAdmin(admin.ModelAdmin):
    list_filter=(
        ("lehrer", admin.RelatedOnlyFieldListFilter), 
    )
    ordering = ('-id',)

class MatheGruppeFilter(admin.RelatedFieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        super().__init__(field, request, params, model, model_admin, field_path)
        self.title = 'Mathegruppe'

class PhysikGruppeFilter(admin.RelatedFieldListFilter):
    def __init__(self, field, request, params, model, model_admin, field_path):
        super().__init__(field, request, params, model, model_admin, field_path)
        self.title = 'Physikgruppe'

class ProfilAdmin(admin.ModelAdmin):
    list_filter = (
        'mathe', 
        'physik',
        ('gruppe', MatheGruppeFilter),
        ('physikgruppe', PhysikGruppeFilter),
    )
    search_fields = ['vorname', 'nachname']
    list_display = ('pk', 'vorname', 'nachname', 'klasse', 'app_kuerzel', 'sso_kuerzel', 'get_mathegruppe_name', 'physikgruppe')

    fieldsets = [
        ('Allgemein', {
            'fields': [('vorname', 'nachname', 'klasse', 'schule'),('mathe', 'physik')]
        }),
        ('SSO', {
            'fields': ['moodle_uid', 'eduplaces_uid'], 
            'classes': ['collapse']
        }),
        ('Mathe-Spezifisch', {
            'fields': [('gruppe', 'jg', 'kurs', 'stufe', 'sj', 'hj', 'katmax')],
            'classes': ['collapse']
        }),
        ('Zeiträume & Weitere Infos', {
            'fields': ['schuljahr_ab', 'halbjahr_ab', 'details', 'keine_hj_frage'], 
            'classes': ['collapse']
        }),
        ('Physik-Spezifisch', {
            'fields': ['physikgruppe'],
            'classes': ['collapse']
        }),
    ]

    @admin.display(description='Mathegruppe', ordering='gruppe')
    def get_mathegruppe_name(self, obj):
        return obj.gruppe

    @admin.display(description='Apps')
    def app_kuerzel(self, obj):
        kuerzel = []
        if obj.mathe:
            kuerzel.append('M')
        if obj.physik:
            kuerzel.append('P')
        return ', '.join(kuerzel) if kuerzel else '–'

    @admin.display(description='SSO')
    def sso_kuerzel(self, obj):
        kuerzel = []
        if obj.moodle_uid:
            kuerzel.append('m')
        if obj.eduplaces_uid:
            kuerzel.append('e')
        return ', '.join(kuerzel) if kuerzel else '–'
    
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
    list_display = ('zeitpunkt', 'consumer_key', 'user_name', 'rolle')
    ordering = ('-zeitpunkt',)


admin.site.unregister(User)
admin.site.register(User,  BenutzerAdmin)  
admin.site.register(Ort, OrtAdmin)
admin.site.register(Schule, SchuleAdmin)
admin.site.register(Profil, ProfilAdmin)
admin.site.register(Lerngruppe, LerngruppeAdmin)
admin.site.register(Geloescht, GeloeschtAdmin)
