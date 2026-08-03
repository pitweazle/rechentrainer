from django import forms
from django.db import models
from datetime import datetime, date

from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from django import forms

from accounts.models import Profil, Ort, Schule, Lerngruppe


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
        fields = ('vorname', 'nachname', 'klasse')


