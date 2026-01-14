from django.conf import settings
from django.conf.urls.static import static

from django.urls import path, include
from .import views

urlpatterns = [
    path('', include("accounts.urls")),
    path('', include("medien.urls")), 
    path('kategorien/', views.kategorien, name='kategorien'),
    path('uebersicht/', views.uebersicht, name='uebersicht'),
    path('uebersicht/<int:schueler_id>/', views.uebersicht, name='schueler_uebersicht'),
    path('protokoll/', views.protokoll, name='protokoll'),
    path('protokoll/<int:schueler_id>/', views.protokoll, name='protokoll'),
    path('details/<int:zeile_id>/', views.details, name='details'),
    path('abbrechen/<int:zaehler_id>', views.abbrechen, name='abbrechen'),
    path('loesung/<int:zaehler_id>/<int:protokoll_id>/', views.loesung, name='loesung'),
    path('hilfe/<int:zaehler_id>/<int:protokoll_id>/', views.hilfe, name='hilfe'),
    path('optionen/<slug:slug>', views.optionen, name='optionen'),
    path('<slug:slug>/', views.main, name='main'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])