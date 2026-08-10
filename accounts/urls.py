from django.urls import path, include
from .import views

urlpatterns = [
    path('', views.index, name='index'),  # Startseite Accounts

    #path("uebersicht/<int:profil_id>/", views.uebersicht, name="uebersicht"),

    # Anmeldung & Registrierung
    path("anmelden/", views.anmelden, name="anmelden"),
    path("rt_profil_ergaenzen/", views.rt_profil_ergaenzen, name="rt_profil_ergaenzen"),
    path("login/", views.anmelden, name="login"), 
    path('logout/', views.custom_logout, name='logout'),
    path("registrieren/", views.registrieren, name="registrieren"),
    path("profil/", views.profil, name="profil"),
    path("account_loeschen/", views.account_loeschen, name="account_loeschen"),

    # SSO Einbindung
    path('lti/launch/', views.lti_launch, name='lti_launch'),
    path('moodle-entscheidung/', views.moodle_entscheidung, name='moodle_entscheidung'),
    path('simulation_moodle/', views.simulation_moodle, name='simulation_moodle'),
    path('physik/simulation/moodle/', views.simulation_moodle, name='simulation_moodle_physik'),
    path('eduplaces/login/', views.eduplaces_login, name='eduplaces_login'),
    path('eduplaces/callback/', views.eduplaces_callback, name='eduplaces_callback'),
    path('eduplaces/logout/', views.eduplaces_logout, name='eduplaces_logout'),
    path('eduplaces/zuordnung/', views.eduplaces_zuordnung, name='eduplaces_zuordnung'),
    path('sim_moodle/', views.simulation_moodle, name='simulation_moodle'),
    path('sim_eduplaces/', views.simulation_eduplaces, name='simulation_eduplaces'),


    # Halbjahres-Operationen
    #path("hj_pruefen/", views.hj_pruefen, name="hj_pruefen"),
    path("neues_halbjahr/", views.neues_halbjahr, name="neues_halbjahr"),
    path("doch_neues_halbjahr/", views.doch_neues_halbjahr, name='doch_neues_halbjahr'),
    path("naechstes_halbjahr/", views.naechstes_halbjahr, name="naechstes_halbjahr"),

    # Wahl-Operationen
    path("ort_wahl/", views.ort_wahl, name="ort_wahl"),
    path("schule_wahl/<schule_id>/", views.schule_wahl, name="schule_wahl"),
    path("lehrer_wahl/<lehrer_id>/", views.lehrer_wahl, name="lehrer_wahl"),
    path("gruppe_wahl/<gruppe_id>/", views.gruppe_wahl, name="gruppe_wahl"),
    path("gruppe_fertig/", views.gruppe_fertig, name="gruppe_fertig"),

    # Gruppen & Schüler
    path("meine_gruppen/", views.meine_gruppen, name="meine_gruppen"),
    path("neue_gruppe/", views.neue_gruppe, name="neue_gruppe"),
    path("gruppe_uebersicht/<int:gruppe_id>/", views.gruppe_uebersicht, name="gruppe_uebersicht"),
    path("gruppe_aendern/<int:gruppe_id>/", views.gruppe_aendern, name="gruppe_aendern"),
    path("gruppe_loeschen/<int:gruppe_id>/", views.gruppe_loeschen, name="gruppe_loeschen"),
    path("mein_schueler/<schueler_id>/<hj_stimmt>/", views.mein_schueler, name="mein_schueler"),
    path("schueler_aendern/<schueler_id>/", views.schueler_aendern, name="schueler_aendern"),

    # Sonstiges
    path("profil_lehrer/", views.profil_lehrer, name="profil_lehrer"),
    path("aufgaben_loeschen/<int:lehrer_id>/", views.aufgaben_loeschen, name="aufgaben_loeschen"),
    path("stufen/", views.stufen, name="stufen"),
    path("suchen/<int:gruppe_id>/", views.suchen, name="suchen"),
    #path("suchen/", views.suchen, name="suchen"),
    path("datenschutz/", views.datenschutz, name="datenschutz"),
    path("stimmen/", views.stimmen, name="stimmen"),
    path("bestenliste/", views.bestenliste, name="bestenliste"),
    path("statistik/", views.statistik, name="statistik"),
    path("alle_lehrer/", views.alle_lehrer, name="alle_lehrer"),

    # Auth-URLs Django
    path("", include("django.contrib.auth.urls")),
 ]
