from django.urls import path, include
from .import views

urlpatterns = [
    path("duell_uebersicht/<int:gruppe_id>/", views.duell_uebersicht, name="duell_uebersicht"),
    path("duell_start/", views.duell_start, name="duell_start"),
    path("duellant_aendern/<int:gruppe_id>/<int:duellant_id>/", views.duellant_aendern, name="duellant_aendern"),
    path('duell_aufgabe/<slug:slug>/', views.duell_aufgabe, name='duell_aufgabe'),
    path('duell_kontrolle/', views.duell_kontrolle, name='duell_kontrolle'),
    path('duellant_edit/<int:duellant_id>/<str:punkte>/', views.duellant_edit, name='duellant_edit'),
    path('duell_auslosen/', views.duell_auslosen, name='duell_auslosen'),
    path('duell_loesung/', views.duell_loesung, name='duell_loesung'),
]