from sched import scheduler
from django.contrib.auth.models import User
from django.db import models

from django import forms
from django.db.models import IntegerField
from django.utils.text import slugify
#from django.core.exceptions import ValidationError

#from django.contrib.postgres.fields import ArrayField
from django.core import validators
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from accounts.models import Profil, Lerngruppe

class wahl_farbe(models.TextChoices):
    Gruppe_A = 'background-color: #B0E2FF',
    Gruppe_B = 'background-color: #9AFF9A',
    Gruppe_C = 'background-color: #FFFACD',
    Gruppe_D = 'background-color: #FFDEAD',
    Gruppe_E = 'background-color: #FFB5C5',  

class Kategorie(models.Model):
    zeile = models.PositiveSmallIntegerField(default=0, unique=True)             # entspricht der Aufgabengruppe (1 bis 35)
    name = models.CharField(max_length=30)
    farbe= models.CharField(max_length=25, choices=wahl_farbe.choices)

    start_jg = models.PositiveSmallIntegerField(default=5, verbose_name="Start in Jahrgang")
    start_sw = models.PositiveSmallIntegerField(default=1, verbose_name="Start in Schulwoche")

    eof = models.PositiveSmallIntegerField(default=10, verbose_name="Eingaben ohne Fehler")  # Aufgaben die an einem Stück richtig beantwortet werden müssen damit der Fehlerzähler zurückgesetzt wird

    slug=models.SlugField(default="", null=False)

    def save(self, *args, **kwargs):
        self.slug=slugify(self.name)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.slug

    class Meta:
        verbose_name = 'Kategorie'
        verbose_name_plural = 'Kategorien'

class Auswahl(models.Model):
    kategorie = models.ForeignKey(Kategorie, null=True, on_delete=models.CASCADE)
    text = models.CharField(max_length=80, verbose_name="Text")
    bis_stufe = models.IntegerField(default=0, verbose_name="bis einschl. Stufe:")
    bis_jg = models.IntegerField(default=0, verbose_name="bis einschl. Jahrgang:")
    update = models.BooleanField(default = True)

    def __str__(self):
        return self.text 

    class Meta:
        verbose_name = 'Auswahl'
        verbose_name_plural = 'Auswahl'

class Hilfe(models.Model):
    kategorie = models.ForeignKey(Kategorie, on_delete=models.CASCADE, related_name="hilfe")
    hilfe_id = models.SmallIntegerField(default=0)
    text = models.TextField(blank=True)
    def __str__(self):
        return f"({self.kategorie}: {self.hilfe_id}: {self.text})"

    class Meta:
        #unique_together = ['kategorie', 'hilfe_id']
        verbose_name_plural = 'Hilfen'

class Protokoll(models.Model):
    profil = models.ForeignKey(Profil, verbose_name='Benutzer', related_name='protokolle', on_delete=models.CASCADE)
    #gewertet werden nur die Aufgaben des jeweiligen Schuljabjahres, im Januar, Juni und August, kann der user aber auch schon festlegen, dass die Aufgaben für das nächste Schulhalbjahr gelten:
    sj = models.SmallIntegerField(default=0)
    hj = models.SmallIntegerField(default=0)

    kategorie = models.ForeignKey(Kategorie, related_name='protokolle', on_delete=models.CASCADE)
    titel = models.CharField(max_length=25, blank=True)
    typ = models.SmallIntegerField(default=0) 
    typ2 = models.SmallIntegerField(default=0) 
     
    aufgnr = models.PositiveSmallIntegerField(default=0) 
    
    #der Aufgabentext:
    text = models.TextField(blank=True)
    pro_text = models.CharField(max_length=100, blank=True)
    variable = models.JSONField()
    frage = models.CharField(max_length=20, blank=True)
    einheit = models.CharField(max_length=20, blank=True)
    anmerkung = models.CharField(max_length=100, blank=True)
   
    parameter = models.JSONField()
 
    #hier speichere ich die Lösung, wahlweise als zahl, u.U. auch (mehrere) Lösungen als String:
    wert = models.DecimalField('Wert', null=True, max_digits=20, decimal_places=7)
    loesung = models.JSONField()                                                    #hier können mehrere Werte eingegeben werden, der erste wird angezeigt wenn "Lösung anzeigen" angeklickt wird. Steht hier auch "indiv" so wird die Eingabe in der jeweiligen Funktion überprüft

    #hilfe = models.TextField(blank=True)
    hilfe_id = models.SmallIntegerField(default=0)
    
    #die Eingabe des users:
    eingabe = models.CharField(max_length=20, blank=True)

    versuche = models.PositiveSmallIntegerField('Versuche', default=0)
    #Eintrag richtig, falsch, Extrapunkte, Lösung anzeigen, Abbruch:
    wertung = models.CharField(max_length=10, blank=True)
    richtig = models.DecimalField(max_digits=3, decimal_places=1, default=0)

    falsch = models.PositiveSmallIntegerField(default=0)  
    abbr = models.BooleanField(default=True)
    lsg = models.BooleanField(default=False)    
    hilfe = models.BooleanField(default=False)  
    
    start = models.DateTimeField('Start', auto_now_add=True)
    end = models.DateTimeField('Ende', blank=True, null=True, default=None)
    #szeit=models.FloatField(default=0)

    @property
    def dauer(self):
        if not self.end:
            return 0
        return (self.end - self.start).total_seconds()

    def zweigabe(self):
        return self.eingabe.replace(".",",")
    
    # def farbe(self):                        # wird im Duell_Protokoll benötigt
    #     if self.richtig > 0:
    #         farbe = "gruen"
    #     elif self.richtig <0:
    #         farbe = "rot"
    #     else:
    #         farbe = "null"
    #     return farbe
        
    def name(self):        
        return f"{self.profil.nachname}, {self.profil.vorname}, {self.profil.klasse}, {self.profil.gruppe}"

    class Meta:
        verbose_name = 'Protokoll'
        verbose_name_plural = 'Protokolle'

class Zaehler(models.Model):
    profil = models.ForeignKey(Profil, verbose_name='Benutzer', related_name='zaehler', on_delete=models.CASCADE) 
    kategorie = models.ForeignKey(Kategorie, on_delete=models.CASCADE, related_name="zaehler")
    letzte = models.DateTimeField('Letzte Bearbeitung', auto_now_add=True)
    
    sj = models.SmallIntegerField(default=0)
    hj = models.SmallIntegerField(default=0)  
    optionen_text=models.CharField(max_length=40, blank=True, default="", verbose_name="Optionen")
    typ_anf = models.SmallIntegerField(default=0)        
    typ_end = models.SmallIntegerField(default=0)    
    aufgnr = models.PositiveSmallIntegerField(default=0)  
    richtig_of = models.PositiveSmallIntegerField(default=0)
    fehler_ab = models.DateTimeField(auto_now_add=True)
    fehler_zaehler = models.SmallIntegerField(default=0) 
    abbr_zaehler = models.SmallIntegerField(default=0)     
    hilfe_zaehler = models.SmallIntegerField(default=0) 
    lsg_zaehler = models.SmallIntegerField(default=0) 
    hinweis = models.CharField(max_length=100, blank=True)
    #bonus = models.SmallIntegerField(default=0)

    letzter_typ = models.SmallIntegerField(default=0)
    reihenfolge = models.JSONField(null=True, blank=True, default=list)

    def __str__(self):
        return f"({self.id}, {self.profil}, {self.profil.user}, {self.kategorie}, {self.sj})/{self.hj})"
    
    class Meta:
        unique_together = ['kategorie', 'profil']
        verbose_name = 'Zähler'
        verbose_name_plural = 'Zähler'   

class Sachaufgabe(models.Model):
    lfd_nr = models.SmallIntegerField(default=0, unique=True)
    ab_jg = models.SmallIntegerField(default=0)
    text = models.TextField()
    variable = models.JSONField(help_text="z.B.:{'a': [5, 5.5, 6, 6.5, 7], 'b': [[2, 'zwei'], [4, 'vier']]}")
    loesung = models.CharField(max_length=50, help_text="z.B.: {c}*{a:.2f}+{d}*{b:.2f}={:.2f}")
    pro_text = models.CharField(max_length=25)
    anmerkung = models.CharField(max_length=50, null=True, blank=True)
    links_text = models.CharField(max_length=25)
    rechts_text = models.CharField(max_length=25)
    def __str__(self):       
        return f"{self.lfd_nr}: {self.text}, {self.ab_jg}"
    class Meta:
        verbose_name_plural = 'Sachaufgaben'
