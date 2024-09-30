from django import forms
from django.db import models

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Profil, Ort, Schule, Lerngruppe

class wahl_kurs(models.TextChoices):
    GYMNASIUM = 'Y', 'Gymnasium'
    REALSCHULE = 'R', 'Realschule'
    HAUPTSCHULE = 'H', 'Hauptschule'
    E_KURS = 'E', 'E-Kurs'
    G_KURS = 'G', 'G-Kurs'
    A_KURS = 'A', 'A-Kurs'
    B_KURS = 'B', 'B-Kurs'
    C_KURS = 'C', 'C-Kurs'
    FOERDER = 'i', 'Förderschüler'

class Login_Form(forms.Form):
    username = forms.CharField(label='Benutzername', localize=True)
    password = forms.CharField(widget=forms.PasswordInput, label='Passwort')

class Register_Form(UserCreationForm):
    class Meta:
        model = User
        fields = ["username",  "password1", "password2", "email",]
        help_texts = {'username': "Achte darauf, dass zwischen großen und kleinen Buchstaben unetrschieden wird - schreibe dir deinen Usernamen am besten auf!"}
    def save(self, commit=True):
        user = super().save(commit=False)
        if commit:
            user.save()
            return user

class Profil_Form(forms.ModelForm):
    class Meta:
        model = Profil
        labels = {
            'jg': 'Jahrgang',
        }
        fields = ('vorname', 'nachname', 'klasse', 'jg', 'kurs',)
        widgets = {'jg': forms.TextInput(attrs={'size': 2}), 
        'klasse': forms.TextInput(attrs={'size': 10}),
        }

class Profil_Aendern_Form(forms.ModelForm):
    class Meta:
        model = Profil
        fields = ('klasse',)
        widgets = {'klasse': forms.TextInput(attrs={'size': 10})}

class Lehrer_Aendern_Form(forms.ModelForm):
    class Meta:
        model = Profil
        fields = ['vorname', 'nachname', 'schule', 'zweite_schule', 'jg', 'kurs', 'stufe']
        labels = {
            'zweite_schule': 'zweite Schule',
        }
        help_texts = {'stufe': "Vor Änderung der Stufe bitte die Anleitung lesen!"}
        widgets = {'jg': forms.TextInput(attrs={'size': 2}), 
                'klasse': forms.TextInput(attrs={'size': 10}),
                'stufe': forms.TextInput(attrs={'size': 2}),
                'sj': forms.TextInput(attrs={'size': 4}),
                'hj': forms.TextInput(attrs={'size': 1}),}

class Ort_Form(forms.Form):
    ort = forms.ModelChoiceField(queryset=Ort.objects.all().order_by('plz'), widget=forms.Select, required=False)

class Schule_Form(forms.Form):
    schule = forms.ModelChoiceField(queryset=Schule.objects.all().order_by('schulname'), widget=forms.Select, required=False)

class Gruppe_Form(forms.Form):
    gruppe = forms.ModelChoiceField(label="meine Lerngruppe", queryset=Lerngruppe.objects.all(), widget=forms.Select, required=False)

class Gruppe_Aendern_Form(forms.ModelForm):
    class Meta:
        model = Lerngruppe
        fields = ['name', 'jg', 'aufgaben_pro_woche', 'note_anzeigen']
        labels = {'name': "Gruppenname",
            'aufgaben_pro_woche': 'Aufgaben pro Woche',
        }
        widgets = {
            'aufgaben_pro_woche': forms.NumberInput(attrs={
                'max': '120',    # For maximum number
                'min': '0',    # For minimum number
            }),
        }
        help_texts = {'aufgaben_pro_woche': "Wenn hier Null steht, gilt die Voreinstellung - danach sollen die Schülerinnen und Schüler 10 Aufgaben pro Woche und Jahrgang rechnen (z.B.: 70 im Jahrgang 7) - hier kann aber auch ein anderer Wert eingegeben werden."}

class Gruppe_Neu_Form(forms.ModelForm):
    class Meta:
        model = Lerngruppe
        fields = ['name', 'jg', 'aufgaben_pro_woche', 'note_anzeigen']
        labels = {'name': "Gruppenname",
            'aufgaben_pro_woche': 'Aufgaben pro Woche',
        }
        help_texts = {'name': 'Das kann einfach der Name der Klasse sein oder die Kursbezeichnung aus dem Stundenplan - die Schülerinnen und Schüler sollten ihre Lerngruppe an diesem Namen erkennen können.',
                      'aufgaben_pro_woche': "Wenn hier Null steht, gilt die Voreinstellung - danach sollen die Schülerinnen und Schüler 10 Aufgaben pro Woche und Jahrgang rechnen (z.B.: 70 im Jahrgang 7) - hier kann aber auch ein anderer Wert eingegeben werden."}

class ProtokollFilter_Gruppe(forms.Form):
    auswahl = forms.ChoiceField(label='', choices=[("Halbjahr",'aktuelles Halbjahr'),('Woche','Woche'), ('8 Tage','8 Tage'), ('9 Tage','9 Tage'), ("Schuljahr",'aktuelles Schuljahr'), ('heute','heute'), ("all",'Alle Aufgaben'),("next",'nächstes Halbjahr'), ])

# class Datum_Form(forms.Form):
#     aufgaben_seit = forms.DateField(label="", widget = forms.SelectDateWidget())

class Schueler_Aendern_Form(forms.ModelForm):
    class Meta:
        model = Profil
        fields = ['vorname', 'nachname', 'klasse', 'jg', 'kurs' , 'stufe', 'schule', 'gruppe', 'sj', 'hj']
        help_texts = {'stufe': "Vor Änderung der Stufe bitte die Anleitung lesen!"}
        widgets = {'jg': forms.TextInput(attrs={'size': 2}), 
                'klasse': forms.TextInput(attrs={'size': 10}),
                'stufe': forms.TextInput(attrs={'size': 2}),
                'sj': forms.TextInput(attrs={'size': 4}),
                'hj': forms.TextInput(attrs={'size': 1}),}

class Suchen_Form(forms.Form):
    vorname = forms.CharField(label="Vorname", max_length=50, required=False)
    nachname = forms.CharField(label="Nachname", max_length=50, required=False)
    
class Zusammen_Form(forms.Form):
    quelle = forms.IntegerField(label="Quelle",  required=False)
    ziel = forms.IntegerField(label="Ziel", required=False, help_text="Bitte ID eingeben")

    widgets = {'quelle': forms.TextInput(attrs={'size': 6}), 
        'ziel': forms.TextInput(attrs={'size': 6}),
        }
    
class Loeschen_Form(forms.Form):
    loeschen = forms.IntegerField(label="Accounts löschen", required=False, help_text="Bitte ID eingeben")

class Abmelden_Form(forms.Form):
    abmelden = forms.IntegerField(label="Mitglied entfernen", required=False, help_text="Bitte ID eingeben")



