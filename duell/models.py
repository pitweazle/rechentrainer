from django.db import models
from accounts.models import Profil, Lerngruppe
from core.models import Protokoll

class Duellant(models.Model):
    LIGAWAHL = (
        ("A", "A"),
        ("B", "B"),
        ("C", "C")
    )
    profil = models.OneToOneField(Profil, related_name='duellprofil', on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    liga = models.CharField(max_length=1, choices=LIGAWAHL, default="A")
    platz = models.SmallIntegerField(null=True, blank=True)
    aufsteiger = models.BooleanField(default=False)
    abwesend = models.BooleanField(default=False)
    spiele = models.SmallIntegerField(default=0)
    punkte = models.DecimalField(max_digits=3, decimal_places=1, default=0)
    punkte_spiel = models.DecimalField(max_digits=2, decimal_places=1, default=0)
    pps = models.DecimalField(max_digits=4, decimal_places=2, default=0) 
    class Meta:
        verbose_name_plural = 'Duellanten'
    
    def __str__(self):
        return f"{self.profil.vorname}_{self.profil.nachname}"

class Duell_Protokoll(models.Model):
    protokoll = models.ForeignKey(Protokoll, related_name='duellprotokoll', on_delete=models.CASCADE)
    gruppe = models.ForeignKey(Lerngruppe, related_name='duellgruppe', on_delete=models.CASCADE)
    duellant_1 = models.ForeignKey(Duellant, related_name='duellant_1', on_delete=models.CASCADE)
    duellant_2 = models.ForeignKey(Duellant, related_name='duellant_2', on_delete=models.CASCADE)
    wertung = models.JSONField()

    def name(self):        
        return f"{self.gruppe}: {self.duellant_1} vs {self.duellant_2}"

    class Meta:
        verbose_name = 'Duell_Protokoll'
        verbose_name_plural = 'Duell_Protokolle'