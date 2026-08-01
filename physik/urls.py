from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from . import views

app_name = "physik"

urlpatterns = [
    path('', views.index, name='index'),
    path("registrieren/", views.registrieren, name="registrieren"),
    path("anmelden/", views.anmelden, name="anmelden"),
    path("login/", views.anmelden, name="login"),
    path('logout/', views.force_logout, name='logout'),

    path('view-einstellung/<str:slug>/', views.update_view_settings, name='update_view_settings'),
    path('row-einstellung/<str:slug>/', views.update_row_settings, name='update_row_settings'),
    path("aufgaben/", views.aufgaben, name="aufgaben"),

    #path('check-answer/', check_answer, name='check_answer'),

    path('inventar/', views.aufgaben_liste, name='aufgaben_liste'),
    path('aufgabe/<int:pk>/', views.aufgabe_einstellungen, name='aufgabe_einstellungen'),
    path('analyse/', views.fehler_liste, name='fehler_liste'),
    path('analyse/edit/<int:log_id>/', views.fehler_edit, name='fehler_edit'),
    path("call/<str:lfd_nr>/", views.call, name="call"),

    path("howto/", views.howto, name="howto"),
    path('accounts/', include('django.contrib.auth.urls')),
    path("datenschutz/", views.datenschutz, name="datenschutz"),
]

