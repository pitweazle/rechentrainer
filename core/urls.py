from django.urls import path, include
from .import views

urlpatterns = [
    path('', include("accounts.urls")), 
    path('kategorien/', views.kategorien, name='kategorien'),
    path('uebersicht/', views.uebersicht, name='uebersicht'),
    path('uebersicht/<int:schueler_id>/', views.uebersicht, name='schueler_uebersicht'),
    path('protokoll/', views.protokoll, name='protokoll'),
    path('protokoll/<int:schueler_id>/', views.protokoll, name='protokoll'),
    path('details/<int:zeile_id>/', views.details, name='details'),
    path('abbrechen/<int:zaehler_id>', views.abbrechen, name='abbrechen'),
    path('loesung/<int:zaehler_id>/<int:protokoll_id>/', views.loesung, name='loesung'),
    path('hilfe/<int:zaehler_id>/<int:protokoll_id>/', views.hilfe, name='hilfe'),
    path('<slug:slug>/', views.main, name='main'),
    path('optionen/<slug:slug>', views.optionen, name='optionen'),
]
