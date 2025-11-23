from django.contrib import admin
from .models import Test, TestEinstellung

class TestEinstellungInline(admin.TabularInline):
    model = TestEinstellung
    extra = 0
    fields = ("kategorie", "anzahl", "optionen_text", "typ_anf", "typ_end", "reihenfolge")

@admin.register(Test)
class TestAdmin(admin.ModelAdmin):
    list_display = ("name", "gruppe", "lehrer_anzeige", "aktiv")
    list_filter = (
        "aktiv",
        ("gruppe", admin.RelatedOnlyFieldListFilter),
        ("gruppe__lehrer", admin.RelatedOnlyFieldListFilter),  # <- wichtig
    )
    search_fields = ("name",)
    ordering = ("-id",)
    readonly_fields = ("proto_marker", "created_at")
    inlines = [TestEinstellungInline]
    readonly_fields = ("proto_marker", "created_at")

    fieldsets = [
        (None, {
            'fields': ['gruppe', 'name', 'aktiv'],
        }),
        ('weitere Infos', {
            'fields': ['proto_marker', 'created_at'],
            'classes': ['collapse'],   # <- klappt diesen Abschnitt ein
        }),
    ]

    def lehrer_anzeige(self, obj):
        u = getattr(obj.gruppe, "lehrer", None)
        if not u:
            return "–"
        p = getattr(u, "profil", None)
        if p and (p.vorname or p.nachname):
            return f"{p.vorname} {p.nachname}".strip()
        return u.username  # Fallback
    lehrer_anzeige.short_description = "Lehrkraft"

@admin.register(TestEinstellung)
class TestEinstellungAdmin(admin.ModelAdmin):
    list_display = ("test", "get_gruppe", "get_lehrkraft", "kategorie", "anzahl", "optionen_text", "typ_anf", "typ_end", "reihenfolge")
    list_filter  = ("test",  ("test__gruppe", admin.RelatedOnlyFieldListFilter))
    search_fields = ("test__name",)
    readonly_fields = ("optionen_text",)
    ordering = ("test", "kategorie",)

    @admin.display(description="Gruppe", ordering="test__gruppe__name")
    def get_gruppe(self, obj):
        return getattr(getattr(obj.test, "gruppe", None), "name", "-")

    @admin.display(description="Lehrkraft", ordering="test__gruppe__lehrer__profil__nachname")
    def get_lehrkraft(self, obj):
        """Zeigt Nachname, Vorname der Lehrkraft (aus Profil), sonst Username."""
        lehrer = getattr(obj.test.gruppe, "lehrer", None)
        if not lehrer:
            return "-"
        profil = getattr(lehrer, "profil", None)
        if profil and (profil.vorname or profil.nachname):
            return f"{profil.vorname} {profil.nachname}".strip(", ")
        return lehrer.get_full_name() or lehrer.username