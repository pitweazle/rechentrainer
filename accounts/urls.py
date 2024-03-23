from django.urls import path, include
from .import views

urlpatterns = [
    path('', views.index, name='index'),
    path("anmelden/", views.anmelden, name="anmelden"),
    path("accounts/login/", views.anmelden, name="anmelden"),

    path("hj_pruefen/", views.hj_pruefen, name="hj_pruefen"),
    path("neues_halbjahr/", views.neues_halbjahr, name="neues_halbjahr"),
    path("doch_neues_halbjahr/", views.doch_neues_halbjahr, name='doch_neues_halbjahr'),
    path("naechstes_halbjahr/", views.naechstes_halbjahr, name="naechstes_halbjahr"),

    path("registrieren/", views.registrieren, name="registrieren"),
    path("profil/", views.profil, name="profil"), 
    path("account_loeschen/", views.account_loeschen, name="account_loeschen"),

    path("ort_wahl/", views.ort_wahl, name="ort_wahl"),
    path("schule_wahl/<schule_id>/", views.schule_wahl, name="schule_wahl"), 
    path("lehrer_wahl/<lehrer_id>/", views.lehrer_wahl, name="lehrer_wahl"), 
    path("gruppe_wahl/<gruppe_id>/", views.gruppe_wahl, name="gruppe_wahl"),

    path("gruppe_fertig/", views.gruppe_fertig, name="gruppe_fertig"),
    path("gruppe_uebersicht/<int:gruppe_id>/", views.gruppe_uebersicht, name="gruppe_uebersicht"),
    path("gruppe_aendern/<int:gruppe_id>/", views.gruppe_aendern, name="gruppe_aendern"),
    path("gruppe_loeschen/<int:gruppe_id>/", views.gruppe_loeschen, name="gruppe_loeschen"),
     path("suchen/<int:gruppe_id>/", views.suchen, name="suchen"),

    path("mein_schueler/<schueler_id>/<hj_stimmt>/", views.mein_schueler, name="mein_schueler"),
    path("schueler_aendern/<schueler_id>/", views.schueler_aendern, name="schueler_aendern"),

    path("profil_lehrer/", views.profil_lehrer, name="profil_lehrer"), 
    path("aufgaben_loeschen/<int:lehrer_id>/", views.aufgaben_loeschen, name="aufgaben_loeschen"),

    path("meine_gruppen/", views.meine_gruppen, name="meine_gruppen"),
    path("neue_gruppe/", views.neue_gruppe, name="neue_gruppe"),

    path("datenschutz/", views.datenschutz, name="datenschutz"),
    path("stimmen/", views.stimmen, name="stimmen"),
    path("stufen/", views.stufen, name="stufen"),

    path("film/", views.film, name="film"),
    path("installation_film/", views.installation_film, name="installation_film"),
    path("weitere_aufgaben/", views.weitere_aufgaben, name="weitere_aufgaben"),
    path("lernkontrollen/", views.lernkontrollen, name="lernkontrollen"),
    path("download_rechentrainer/", views.download_rechentrainer, name="download_rechentrainer"),
    
    path("update/", views.update),
    path("reparatur/<id>", views.reparatur),

    path("suchen/", views.suchen, name="suchen"),
    
    path("", include("django.contrib.auth.urls")),
]