from django import forms
from .models import Kategorie, Sachaufgabe

class AufgabeFormZahl(forms.Form):
    eingabe = forms.DecimalField(label='', localize=True, max_digits=15, decimal_places=5, widget=forms.NumberInput(attrs={'autofocus': True, 'autocomplete': 'off'}))
    
class AufgabeFormStr(forms.Form):
    eingabe = forms.CharField(label='', localize=True, widget=forms.TextInput(attrs={'autofocus': True, 'autocomplete': 'off'}))

class AufgabeFormTab(forms.Form):
    y2 = forms.DecimalField(label='', max_digits=5,
                                decimal_places=2, required=False, localize=True, widget=forms.TextInput(attrs={'size': 3, 'autocomplete': 'off', 'autofocus': True,}))
    y3 = forms.DecimalField(label='', max_digits=5,
                                decimal_places=2, required=False, localize=True, widget=forms.TextInput(attrs={'size': 3, 'autocomplete': 'off'}))
    y4 = forms.DecimalField(label='', max_digits=5,
                                decimal_places=2, required=False, localize=True, widget=forms.TextInput(attrs={'size': 3, 'autocomplete': 'off'}))
    
class AufgabeFormTerm(forms.Form):
    y0 = forms.DecimalField(label='', max_digits=5,
                                decimal_places=2, required=False, localize=True, widget=forms.TextInput(attrs={'size': 3, 'autocomplete': 'off', 'autofocus': True,}))
    y1 = forms.DecimalField(label='', max_digits=5,
                                decimal_places=2, required=False, localize=True, widget=forms.TextInput(attrs={'size': 3, 'autocomplete': 'off'}))
    y2 = forms.DecimalField(label='', max_digits=5,
                                decimal_places=2, required=False, localize=True, widget=forms.TextInput(attrs={'size': 3, 'autocomplete': 'off'}))
    y3 = forms.DecimalField(label='', max_digits=5,
                                decimal_places=2, required=False, localize=True, widget=forms.TextInput(attrs={'size': 3, 'autocomplete': 'off'}))
    y4 = forms.DecimalField(label='', max_digits=5,
                                decimal_places=2, required=False, localize=True, widget=forms.TextInput(attrs={'size': 3, 'autocomplete': 'off'}))
    
class AuswahlForm(forms.Form):
    optionen = forms.ModelMultipleChoiceField(
        queryset=Kategorie.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    def __init__(self, *args, kategorie=None, profil=None, **kwargs):
        super().__init__(*args, **kwargs)
        if kategorie is not None and profil is not None:
            self.fields['optionen'].queryset = kategorie.auswahl_set.filter(
                bis_jg__gte=profil.jg,
                bis_stufe__gte=profil.stufe
            )

class ProtokollFilter(forms.Form):
    auswahl = forms.ChoiceField(label='Filter', choices=[('heute','heute'), ('Woche','Woche'), ("Halbjahr",'aktuelles Halbjahr'), ("Schuljahr",'aktuelles Schuljahr'),("all",'Alle Aufgaben'),])
 
class ProtokollFilter_neu(forms.Form):
    auswahl = forms.ChoiceField(label='Filter', choices=[("next",'nächstes Halbjahr'), ("Halbjahr",'aktuelles Halbjahr'), ('heute','heute'), ('Woche','Woche'), ("Schuljahr",'aktuelles Schuljahr'),("all",'Alle Aufgaben'),])
 
class Sachaufgaben(forms.ModelForm):
    class Meta:
        model = Sachaufgabe
        fields = '__all__'