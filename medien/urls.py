from django.urls import path, include
from .import views

urlpatterns = [
    path("film/", views.film, name="film"),
    path("installation_film/", views.installation_film, name="installation_film"),
    path("weitere_aufgaben/", views.weitere_aufgaben, name="weitere_aufgaben"),
    path("weitere_projekte/", views.weitere_projekte, name="weitere_projekte"),
    path("lernkontrollen/", views.lernkontrollen, name="lernkontrollen"),
    path("download_rechentrainer/", views.download_rechentrainer, name="download_rechentrainer"),
    path("download_lernbox/", views.download_lernbox, name="download_lernbox"),
]