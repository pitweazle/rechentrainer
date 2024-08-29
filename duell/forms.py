from django import forms
from django.db import models
from .models import Duellant
from core.models import Kategorie
from django.forms import ModelChoiceField

class Duellant_Aendern_Form(forms.ModelForm):
    class Meta:
        model = Duellant
        fields = ['name', 'liga', 'spiele']
        help_texts = {'name': "Keine Leerzeichen - Unterstrich verwenden!"}
        widgets = {'spiele': forms.NumberInput(attrs={'size': 3}),
                   'punkte': forms.NumberInput(attrs={'size': 3})
                    }
        
class Duell_AuswahlForm(forms.Form):
    optionen = forms.ModelMultipleChoiceField(
        queryset=Kategorie.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    def __init__(self, *args, kategorie=None, stufe=None, jg=None, **kwargs):
        super().__init__(*args, **kwargs)
        if kategorie is not None and jg is not None:
            self.fields['optionen'].queryset = kategorie.auswahl_set.filter(
                bis_jg__gte=jg,
                bis_stufe__gte=stufe
            )

class AufgabeFormTab(forms.Form):
    y5 = forms.DecimalField(label='', max_digits=5,
        decimal_places=2, localize=True, widget=forms.TextInput(attrs={'size': 3, 'autocomplete': 'off', 'autofocus': True,}))
    
class DuellProtokollFilter(forms.Form):
    auswahl = forms.ModelChoiceField(queryset=Duellant.objects.filter(profil__gruppe=1), empty_label="(alle)", 
    )

# class DuellProtokollFilter(forms.Form):
#     auswahl = forms.ModelMultipleChoiceField(
#         queryset=Duellant.objects.all(),
#         widget=forms.CheckboxSelectMultiple,
#         required=False,
#     )

#     def __init__(self, *args, gruppe=None, **kwargs):
#         super().__init__(*args, **kwargs)
#         if gruppe is not None :
#             self.fields['auswahl'].queryset = Duellant.auswahl_set.filter(
#                 profil__gruppe = gruppe
#             )
    
