from django.db import models
from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User

class Ort(models.Model):
    name = models.CharField(max_length=50)
    plz = models.PositiveSmallIntegerField(default=0, validators=[MinValueValidator(1000), MaxValueValidator(99999)] )
    
    def __str__(self):
        return f"{self.plz} {self.name}"
    
    class Meta:
        verbose_name_plural = 'Orte'
    
class Schule(models.Model):
    ort = models.ForeignKey(Ort, null=True, on_delete=models.SET_NULL)
    schulname = models.CharField(max_length=50)
    
    def __str__(self):
        return f"{self.schulname}, {self.ort}"
    
    class Meta:
        verbose_name_plural = 'Schulen'
    
class Lerngruppe(models.Model):
    lehrer = models.ForeignKey(User, null=False, on_delete=models.CASCADE, related_name='gruppe')
    name = models.CharField(max_length=15)
    erstellt_am = models.DateField(auto_now_add=True)
    jg = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(13)])
    aufgaben_pro_woche = models.SmallIntegerField(default=0)
    note_anzeigen = models.BooleanField(default = True)
    
    class Meta:
        verbose_name_plural = 'Lerngruppen'
        unique_together = ['lehrer', 'name']
    
    def __str__(self):
        return f"{self.lehrer.profil.nachname}, {self.name}"

class wahl_kurs(models.TextChoices):
    GYMNASIUM = 'Y', 'Gymnasium'
    REALSCHULE = 'R', 'Realschule'
    HAUPTSCHULE = 'H', 'Hauptschule'
    GRUNDSCHULE = 'S', 'Grundschule'
    E_KURS = 'E', 'E-Kurs'
    G_KURS = 'G', 'G-Kurs'
    A_KURS = 'A', 'A-Kurs'
    B_KURS = 'B', 'B-Kurs'
    C_KURS = 'C', 'C-Kurs'
    FOERDER = 'i', 'Förderschüler/in'
    
class Profil(models.Model):
    user = models.OneToOneField(User, related_name='profil', on_delete=models.CASCADE )
    nachname = models.CharField(max_length=30)
    vorname = models.CharField(max_length=30)
    
    klasse = models.CharField(max_length=10)
    # diese Felder werden erst ausgefüllt, wenn ein Schüler seine Lerngruppe wählt
    schule = models.ForeignKey(Schule, related_name='schule1', null= True, blank=True, on_delete = models.SET_NULL)
    zweite_schule = models.ForeignKey(Schule, related_name='schule2',null= True, blank=True, on_delete = models.SET_NULL)
    gruppe = models.ForeignKey(Lerngruppe, null= True, blank=True, on_delete = models.SET_NULL, related_name='gruppe')
    
    jg = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(13)])
    kurs= models.CharField(max_length=1, choices=wahl_kurs.choices, default=wahl_kurs.E_KURS,)

    # werden beim Erstellen eingestellt
    stufe = models.PositiveSmallIntegerField(default=5) #, editable=False)
    sj = models.SmallIntegerField(default=0)
    hj = models.SmallIntegerField(default=0)

    katmax = models.IntegerField(default=0)                                 # die Zeilennummer die höchsten gewählten Aufgabenkategorie
    #voreinst = models.IntegerField(default=1)                               # hier können Voreinstellungen gesetzt und abgefragt werden
    voreinst = models.JSONField(blank=True, null=True, default=dict)
    details = models.BooleanField(default = True)

    def __str__(self):
        return f"{self.pk}, {self.vorname} {self.nachname}, {self.klasse}"

    class Meta:
        verbose_name = 'Profil'
        verbose_name_plural = 'Profile'

class Duell(models.Model):
    profil = models.OneToOneField(Profil, related_name='duellprofil', on_delete=models.CASCADE)
    gruppe = models.ForeignKey(Lerngruppe, null= True, blank=True, on_delete = models.SET_NULL, related_name='duellgruppe')
    liga = models.SmallIntegerField(default=1)
    platz = models.SmallIntegerField(blank=True)
    aufsteiger = models.BooleanField(blank=True)
    krank = models.BooleanField(blank=True)
    spiele = models.SmallIntegerField(default=0)
    punkte = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    spiele = models.SmallIntegerField(default=0)
    pps = models.DecimalField(max_digits=4, decimal_places=2, default=0) 
    
class Geloescht(models.Model):
    user = models.OneToOneField(User, related_name='geloescht', on_delete=models.CASCADE )
    text = models.CharField(max_length=200)
    class Meta:
        verbose_name = 'Gelöscht'
        verbose_name_plural = 'Gelöscht'
 
    def __str__(self):
        return f"{self.user}: {self.text}"
   


    

