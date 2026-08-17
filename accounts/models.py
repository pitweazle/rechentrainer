import uuid
import secrets
import string

from django.db import models
from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User
from django.utils import timezone

class Ort(models.Model):
    name = models.CharField(max_length=50)
    plz = models.CharField(max_length=10, blank=True, null=True)
    
    def __str__(self):
        return f"{self.plz} {self.name}"
    
    class Meta:
        verbose_name_plural = 'Orte'
    
class Schule(models.Model):
    ort = models.ForeignKey(Ort, null=True, on_delete=models.SET_NULL)
    schulname = models.CharField(max_length=50)
    dienststellen_nr = models.CharField(max_length=20, unique=True, null=True, blank=True)
    
    shared_secret = models.CharField(max_length=100, blank=True)

    def save(self, *args, **kwargs):
        if not self.shared_secret:
            self.shared_secret = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(24))
            
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.schulname}, {self.ort}"
    
    class Meta:
        verbose_name_plural = 'Schulen'
    
class Lerngruppe(models.Model):
    lehrer = models.ForeignKey(User, null=False, on_delete=models.CASCADE, related_name='lerngruppen')
    name = models.CharField(max_length=15)
    erstellt_am = models.DateField(auto_now_add=True)
    jg = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(13)])
    aufgaben_pro_woche = models.SmallIntegerField(default=0)
    note_anzeigen = models.BooleanField(default = True)
    alle_aufgaben = models.BooleanField(default = False, 
        verbose_name="Alle Aufgaben", 
        help_text="Alle Aufgaben können gerechnet werden – z.B. für das Üben für einen Test.")
    temp = models.BooleanField(default=False)
    liga = models.BooleanField(default=True)
        
    class Meta:
        verbose_name_plural = 'Lerngruppen'
        unique_together = ['lehrer', 'name']
    
    def __str__(self):
        return f"{self.id} {self.lehrer.profil.nachname}, {self.name}"

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
    BERUF = 'Z', 'Ausbildung/Berufsschule'

class Physikgruppe(models.Model):
    lehrer = models.ForeignKey(User, null=False, on_delete=models.CASCADE, related_name='physikgruppen')
    name = models.CharField(max_length=15)
    erstellt_am = models.DateField(auto_now_add=True)
        
    class Meta:
        verbose_name_plural = 'Physikgruppen'
        unique_together = ['lehrer', 'name']
    
    def __str__(self):
        return f"{self.id} {self.lehrer.profil.nachname}, {self.name}"
    
class Profil(models.Model):
    user = models.OneToOneField(User, related_name='profil', on_delete=models.CASCADE)
    nachname = models.CharField(max_length=30)
    vorname = models.CharField(max_length=30)
    klasse = models.CharField(max_length=10)

    # ERWEITERT FÜR DEINE SSO-SYSTEME
    eduplaces_uid = models.CharField(max_length=255, unique=True, null=True, blank=True)
    moodle_uid = models.CharField(max_length=255, unique=True, null=True, blank=True)

    # diese Felder werden erst ausgefüllt, wenn ein Schüler seine Lerngruppe wählt
    schule = models.ForeignKey(Schule, related_name='schule1', null= True, blank=True, on_delete = models.SET_NULL)
    zweite_schule = models.ForeignKey(Schule, related_name='schule2',null= True, blank=True, on_delete = models.SET_NULL)

    mathe = models.BooleanField(default=False)
    physik = models.BooleanField(default=False)

    # nur für Physik
    physikgruppe = models.ForeignKey(Physikgruppe, null=True, blank=True, on_delete=models.SET_NULL, related_name='profile')

    # nur für Mathe:
    gruppe = models.ForeignKey(Lerngruppe, null=True, blank=True, on_delete=models.SET_NULL, related_name='profile')

    jg = models.PositiveSmallIntegerField(validators=[MinValueValidator(1), MaxValueValidator(13)], null=True, blank=True)
    kurs = models.CharField(max_length=1, choices=wahl_kurs.choices, default=wahl_kurs.E_KURS, null=True, blank=True)

    stufe = models.PositiveSmallIntegerField(default=5, null=True, blank=True)
    sj = models.SmallIntegerField(default=0, null=True, blank=True)
    hj = models.SmallIntegerField(default=0, null=True, blank=True)

    schuljahr_ab = models.DateTimeField(null=True, blank=True)
    halbjahr_ab = models.DateTimeField(null=True, blank=True)

    katmax = models.IntegerField(default=0, null=True, blank=True)                               # die Zeilennummer die höchsten gewählten Aufgabenkategorie
    details = models.BooleanField(default=True)

    keine_hj_frage = models.BooleanField(default = False)

    historische_aufgaben_richtig = models.PositiveIntegerField(default=0)
    historische_aufgaben_falsch = models.PositiveIntegerField(default=0)   

    def __str__(self):
        return f"Username: {self.user}: ({self.id}) {self.vorname} {self.nachname}, {self.klasse}"

    @property
    def anzeige_name(self):
        if self.user.groups.filter(name='Lehrer').exists():
            return f"{self.vorname} {self.nachname}".strip()
        return self.vorname

    class Meta:
        verbose_name = 'Profil'
        verbose_name_plural = 'Profile'
        indexes = [
            models.Index(fields=["gruppe"], name="profil_gruppe"),
        ]

class Geloescht(models.Model):
    benutzername = models.CharField(max_length=50, blank=True)
    grund = models.CharField(max_length=50, null=True, blank=True)
    text = models.TextField(blank=True)
    erstellt_am = models.DateTimeField(default=timezone.now)
    class Meta:
        verbose_name = 'Gelöscht'
        verbose_name_plural = 'Gelöscht'
    def __str__(self):
        return f"{self.erstellt_am}: {self.benutzername}: {self.grund}"

class LoginLog(models.Model):
    zeitpunkt = models.DateTimeField(auto_now_add=True)
    quelle = models.CharField(max_length=50, default='moodle') # z.B. 'moodle' oder 'eduplaces'
    consumer_key = models.CharField(max_length=100, blank=True, null=True)
    user_id = models.CharField(max_length=100, blank=True, null=True)
    user_name = models.CharField(max_length=255, blank=True, null=True)
    rolle = models.CharField(max_length=100, blank=True, null=True)
    institution_name = models.CharField(max_length=255, blank=True, null=True)
    rohdaten = models.TextField()

    def __str__(self):
        return f"[{self.quelle.upper}] {self.institution_name or self.consumer_key} - User: {self.user_id}"

from django.db.models.signals import pre_save
from django.dispatch import receiver

@receiver(pre_save, sender=Profil)
def automatische_schule_fuer_schueler(sender, instance, **kwargs):
    # Wenn das Profil einer Gruppe zugeordnet ist, aber noch keine Schule hat
    if instance.gruppe and not instance.schule:
        lerngruppe = instance.gruppe
        # Prüfen, ob der Lehrer der Gruppe eine Schule im Profil hat
        if lerngruppe.lehrer and hasattr(lerngruppe.lehrer, 'profil') and lerngruppe.lehrer.profil.schule:
            instance.schule = lerngruppe.lehrer.profil.schule

   