from django import forms
from django.db import models
from .models import Duellant

class Duellant_Aendern_Form(forms.ModelForm):
    class Meta:
        model = Duellant
        fields = ['name', 'liga', 'spiele', 'punkte']
        help_texts = {'name': "Keine Leerzeichen - Unterstrich verwenden!"}
        widgets = {'spiele': forms.NumberInput(attrs={'size': 3}),
                   'punkte': forms.NumberInput(attrs={'size': 3})
                    }