from django.urls import path, include
from .import views

urlpatterns = [
    path("duell_uebersicht/<int:gruppe_id>/", views.duell_uebersicht, name="duell_uebersicht"),
    path("duell_start/<int:gruppe_id>/", views.duell_start, name="duell_start"),
    path("duellant_aendern/<int:gruppe_id>/<int:duellant_id>/", views.duellant_aendern, name="duellant_aendern"),
    path('duell_aufgabe/<slug:slug>/', views.duell_aufgabe, name='duell_aufgabe'),
    path('duell_optionen/<slug:slug>/', views.duell_optionen, name='duell_optionen'),
    path('duell_kontrolle/', views.duell_kontrolle, name='duell_kontrolle'),
    path('duellant_edit/<int:duellant_id>/<str:punkte>/', views.duellant_edit, name='duellant_edit'),
    path('neu_auslosen/<str:mit>/', views.neu_auslosen, name='neu_auslosen'),
    path('duell_loesung/', views.duell_loesung, name='duell_loesung'),
    path('duell_loeschen/', views.duell_loeschen, name='duell_loeschen'),
    path('duell_how_to/', views.duell_how_to, name='duell_how_to'),
    path("duell_protokoll/<int:gruppe_id>/", views.duell_protokoll, name="duell_protokoll"),
    
    path("gruppe_temp/", views.gruppe_temp, name="gruppe_temp"),
    path('temp_uebersicht/<int:gruppe_id>/', views.temp_uebersicht, name='temp_uebersicht'),
    path('temp_loeschen/<int:gruppe_id>/<int:id>/', views.temp_loeschen, name='temp_loeschen'),

]