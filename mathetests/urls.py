from django.urls import path
from . import views

urlpatterns = [
    path("test_erstellen/<int:gruppe_id>/", views.test_erstellen, name="test_erstellen"),
    path("test_benennen/<int:gruppe_id>/", views.test_benennen, name="test_benennen"),
    path("test_anzeigen/<int:test_id>/<int:profil_id>/", views.test_anzeigen, name="test_anzeigen"),
    path("test_how_to/", views.test_how_to, name="test_how_to"),


    path('test/<slug:slug>/', views.test, name='test'),
    path("test/<int:test_id>/uebersicht/", views.test_uebersicht, name="test_uebersicht_lehrer"),
    path("tests/<int:test_id>/toggle/", views.test_toggle_aktiv, name="test_toggle_aktiv"),
    path("tests/<int:test_id>/loeschen/", views.test_loeschen, name="test_loeschen"),

    path('test_abbrechen/<int:zaehler_id>/<int:test_id>/', views.abbrechen, name='test_abbrechen'),
    path('test_loesung/<int:zaehler_id>/<int:protokoll_id>/', views.loesung, name='test_loesung'),
]