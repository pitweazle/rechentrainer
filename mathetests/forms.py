from django import forms

from core.models import Auswahl

class TestErstellenForm(forms.Form):
    def __init__(self, *args, **kwargs):
        kategorien = kwargs.pop("kategorien")
        super().__init__(*args, **kwargs)
        for kat in kategorien:
            # Anzahl (optional)
            self.fields[f"kat_{kat.pk}_anzahl"] = forms.IntegerField(
                required=False, min_value=0, max_value=999,
                label=kat.name,
                widget=forms.NumberInput(attrs={
                    "placeholder": "0",
                    "class": "num-input", "inputmode": "numeric", "pattern": "[0-9]*",
                })
            )
            # bis zu 5 Auswahloptionen als Checkboxen
            opts = Auswahl.objects.filter(kategorie=kat).order_by("id")[:5]
            if opts.exists():
                self.fields[f"kat_{kat.pk}_opts"] = forms.MultipleChoiceField(
                    required=False,
                    choices=[(str(o.id), o.text) for o in opts],
                    widget=forms.CheckboxSelectMultiple
                )

class TestNameForm(forms.Form):
    name = forms.CharField(max_length=200, label="Testname")

    NOTENWAHL = [
        ("normal", "Strenge Noten: 95% / 80% / 65% / 50% / 25%"),
        ("weniger streng", "weniger strenge Benotung: 90% / 75% / 60% / 45% / 30%"),
    ]

    note_modus = forms.ChoiceField(
        choices=NOTENWAHL,
        widget=forms.RadioSelect,
        initial="normal",
        label="Notensystem"
    )



