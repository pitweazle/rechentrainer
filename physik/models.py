from django.contrib.auth.models import User
from django.conf import settings
from django.dispatch import receiver
from django.db.models.signals import post_save

from django.db import models

from django.contrib.auth.models import User

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail

class ThemenBereich(models.Model):
    ordnung = models.PositiveSmallIntegerField(unique=True)
    kurz = models.CharField(max_length=2, default="", blank=True)
    thema = models.CharField(max_length=30)
    kapitel_unabhaengig = models.BooleanField(default=False, verbose_name="Kapitel unabhängig")
    farbe = models.CharField(max_length=40,)
    eingeblendet = models.BooleanField(default = True)

    class Meta:
        ordering = ["ordnung"]
        verbose_name = "Themenbereich"
        verbose_name_plural = "Themenbereiche"

    def __str__(self):
        return f"{self.ordnung} – {self.thema}"

class Kapitel(models.Model):
    thema = models.ForeignKey(
        ThemenBereich,
        on_delete=models.CASCADE,
        related_name="kapitel",
    )
    # Sortierung innerhalb eines Themenbereichs (1..n, ohne Obergrenze)
    zeile = models.PositiveSmallIntegerField()
    kapitel = models.CharField(max_length=100)
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["thema", "zeile"],
                name="uniq_kapitel_pro_thema_zeile",
            )
        ]
        ordering = ["thema__ordnung", "zeile"]
        verbose_name = "Kapitel"
        verbose_name_plural = "Kapitel"

    def __str__(self):
        return f"{self.thema.thema} – {self.zeile}: {self.kapitel}"

class Aufgabe(models.Model):
    lfd_nr = models.CharField("lfd_Nr", max_length=10, unique=True)
    thema = models.ForeignKey("ThemenBereich", on_delete=models.CASCADE, related_name="aufgaben")
    kapitel = models.ForeignKey("Kapitel", on_delete=models.CASCADE, related_name="aufgaben")

    EINFACH = 1
    MITTEL = 2
    PROFI = 3
    SCHWIERIGKEIT_CHOICES = [
        (EINFACH, "Einfach"),
        (MITTEL, "Mittel"),
        (PROFI, "Profi"),
    ]
    schwierigkeit = models.PositiveSmallIntegerField(choices=SCHWIERIGKEIT_CHOICES, default=EINFACH)

    # Typ wieder frei editierbar (ohne FK)
    typ = models.CharField("Typ", max_length=20)

    zeichen = models.CharField(
        "Formelzeichen",
        max_length=10,
        blank=True,
        help_text="Optional – wird vor dem Eingabefeld angezeigt (z.B. F=, R=, l=...).",
    )
    frage = models.CharField("Frage", max_length=255)
    einheit = models.CharField(
        "Einheit",
        max_length=10,
        blank=True,
        help_text="Optional – wird hinter dem Eingabefeld angezeigt (z.B. cm, kg, °C).",
    )

    loesung = models.CharField("Antwort", max_length=255, blank=True, help_text="Hier steht die offizielle Antwort.")

    anmerkung = models.CharField("Anmerkung", max_length=255, blank=True, help_text="Optional, nur wenn gewünscht.")
    erklaerung = models.TextField("Erklärung",blank=True,
        help_text="Optional. Wird angezeigt, wenn auf »Lösung« geklickt wird oder eine falsche Eingabe gemacht wurde.",
    )
    hilfe = models.CharField("Hilfe", max_length=255, blank=True, help_text="Optional, nur wenn gewünscht.")

    erstellt = models.DateTimeField("Erstellt", auto_now_add=True)

    von = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="erstellte_aufgaben",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Aufgabe"
        verbose_name_plural = "Aufgaben"

    def __str__(self):
        return f"{self.thema} / {self.kapitel} – {self.frage[:50]}"

    def naechste_lfd_nr(self):
        thema = self.kapitel.thema
        prefix = thema.kurz   # z.B. "E", "O", "W"

        letzte = (
            Aufgabe.objects
            .filter(kapitel__thema=thema, lfd_nr__startswith=prefix)
            .order_by("-lfd_nr")
            .first()
        )

        if not letzte:
            return f"{prefix}001"

        num = int(letzte.lfd_nr[1:]) + 1
        return f"{prefix}{num:03d}"

class AufgabeOption(models.Model):
    aufgabe = models.ForeignKey(Aufgabe, on_delete=models.CASCADE, related_name="optionen")
    position = models.PositiveSmallIntegerField("Position", blank=True, null=True)
    text = models.CharField("Text", max_length=255)

    class Meta:
        verbose_name = "Option"
        verbose_name_plural = "Optionen"
        unique_together = [("aufgabe", "position")]
        ordering = ["position"]

    def save(self, *args, **kwargs):
        if self.position is None: # Falls keine Position eingegeben wurde
            max_pos = AufgabeOption.objects.filter(aufgabe=self.aufgabe).aggregate(
                m=models.Max("position")
            )["m"] or 0
            self.position = max_pos + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.aufgabe_id}:{self.position} {self.text}"

def bild_pfad(instance, filename):
    # WICHTIG: instance ist hier das AufgabeBild-Objekt
    thema = instance.aufgabe.kapitel.thema.thema
    lfd = instance.aufgabe.lfd_nr
    return f"aufgabenbilder/{thema}/{lfd}/{filename}"

class AufgabeBild(models.Model):
    aufgabe = models.ForeignKey(Aufgabe, on_delete=models.CASCADE, related_name="bilder")
    position = models.PositiveSmallIntegerField(blank=True, null=True)
    
    # Hier nur den Namen der Funktion ohne "self" oder "AufgabeBild" angeben
    bild = models.ImageField(upload_to=bild_pfad, null=True, blank=True)
    video = models.FileField(upload_to=bild_pfad, null=True, blank=True)

    class Meta:
        ordering = ["position"]

    def save(self, *args, **kwargs):
        if not self.position:
            max_pos = AufgabeBild.objects.filter(aufgabe=self.aufgabe).aggregate(
                m=models.Max("position")
            )["m"] or 0
            self.position = max_pos + 1
        super().save(*args, **kwargs)

class Protokoll(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    aufgabe = models.ForeignKey('Aufgabe', on_delete=models.CASCADE)
    fach = models.IntegerField(default=2)
    letzte_bearbeitung = models.DateTimeField(auto_now=True)

    class Meta:
        # Sorgt dafür, dass jeder User pro Aufgabe nur einen Lernstand hat
        unique_together = ('user', 'aufgabe')
        verbose_name = "Lernkärtchen-Protokoll"
        verbose_name_plural = "Lernkärtchen-Protokolle"

    def __str__(self):
        return f"{self.user.username}: {self.aufgabe.lfd_nr} -> Fach {self.fach}"

class FehlerLog(models.Model):
    aufgabe = models.ForeignKey(Aufgabe, on_delete=models.CASCADE, related_name="fehler_logs")
    eingegebene_antwort = models.TextField()
    zeitpunkt = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-zeitpunkt']

# @receiver(post_save, sender=Aufgabe) 
# def benachrichtige_mich(sender, instance, created, **kwargs):
#     status = "NEU ERSTELLT" if created else "GEÄNDERT"
    
#     # Wir holen uns die lfd_nr von der Instanz
#     # Falls lfd_nr mal leer sein sollte, nutzen wir .get oder einen Fallback
#     nummer = getattr(instance, 'lfd_nr', 'Unbekannt')

#     betreff = f"PT-Info: Aufgabe Nr. {nummer} {status}"
    
#     nachricht = f"Die Aufgabe mit der laufenden Nummer {nummer} wurde {status.lower()}.\n\n"
#     # Der Link braucht für Django intern meist trotzdem die ID (instance.id), 
#     # da die Admin-URLs auf der Primärschlüssel-ID basieren.
#     nachricht += f"Link zur Aufgabe: https://physiktrainer.app/admin/physik/aufgabe/{instance.id}/change/"
#     empfaenger = ['info@physiktrainer.app'] 

#     send_mail(
    #     betreff,
    #     nachricht,
    #     'info@physiktrainer.app', # Hier jetzt die Artfiles-Adresse
    #     ['info@physiktrainer.app'],
    #     fail_silently=False, 
    # )