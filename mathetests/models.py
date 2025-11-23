from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone

from accounts.models import Lerngruppe

from core.models import Kategorie

class Test(models.Model):
    gruppe = models.ForeignKey(Lerngruppe, on_delete=models.CASCADE, related_name="tests")
    name = models.CharField(max_length=200, unique=True)
    note_streng = models.BooleanField(default=True)
    proto_marker = models.PositiveIntegerField(
        validators=[MinValueValidator(1000)],
        blank=True, null=True,
        help_text="Marker für Protokoll.hilfe (>=1000, eindeutig)",
    )
    aktiv = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ['gruppe', 'name']

    def __str__(self):
        return f"{self.name} ({self.gruppe.name})"

    def assign_proto_marker(self):
        base = 1000 + (self.gruppe_id or 0) + (self.pk or 0)
        marker = base
        while Test.objects.filter(proto_marker=marker).exists():
            marker += 1
        self.proto_marker = marker

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating and not self.proto_marker:
            self.assign_proto_marker()
            super().save(update_fields=["proto_marker"])

class TestEinstellung(models.Model):
    test = models.ForeignKey(Test, on_delete=models.CASCADE, related_name="einstellungen")
    kategorie = models.ForeignKey(Kategorie, on_delete=models.CASCADE)
    anzahl = models.PositiveSmallIntegerField(validators=[MinValueValidator(0)])

    typ_anf = models.SmallIntegerField(default=0)
    typ_end = models.SmallIntegerField(default=0)
    reihenfolge = models.JSONField(null=True, blank=True, default=list)

    optionen_text = models.CharField(max_length=100, blank=True, default="", verbose_name="Optionen")

    class Meta:
        unique_together = ("test", "kategorie")
        ordering = ["kategorie__zeile"]
        verbose_name = "Testeinstellung"
        verbose_name_plural = "Testeinstellungen"

    def __str__(self):
        return f"{self.test.name} – {self.kategorie.name} ({self.anzahl})"
