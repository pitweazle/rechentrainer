import math
import decimal
import string
import random
import re

from py_expression_eval import Parser

#from decimal import Decimal
from fractions import Fraction
from math import gcd


from datetime import date, datetime, timedelta

from django.contrib import messages
from django.contrib.auth.models import User
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from django.http import HttpResponse, HttpResponseNotFound
from django.shortcuts import redirect

from .forms import AufgabeFormZahl, AufgabeFormStr, AufgabeFormTab, AufgabeFormTerm
from .forms import AuswahlForm, ProtokollFilter, ProtokollFilter_neu

from .models import Kategorie, Protokoll, Zaehler, Hilfe, Sachaufgabe
from .models import Profil
from .models import Auswahl

from django.db.models import Sum, F, Count, Q, Max, Avg
from accounts.views import name_hj, name_next_hj, hj_pruefen, quote_farbe

#Hier kommen zunächst die einzelnen Funktionen für die Kategorien (default dient als Beispiel für den Aufbau):<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
def format_zahl(wert, stellen=2, trailing_zeros=True):
    text = f"{wert:.{stellen}f}".replace(".", ",")
    return text.rstrip(",0") if not trailing_zeros and "," in text else text

def addieren(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "":
        typ_anf = 1
        typ_end = 1
        if stufe >= 6 or jg >= 7 or "mit" in optionen:
            typ_end = 2
        return typ_anf, typ_end
    else:
        typ = random.randint(typ_anf, typ_end) 
        typ2 = 0 
        titel = "Addieren" 
        faktor = stufe%2+1                                  #2 für E-Kurs, 1 für G-Kurs und i
        if typ_end>1:
            typ = random.randint(typ_anf, typ_end+1)
    # hier wird die Aufgabe erstellt:
        if typ == 1:
            zahl1 = random.randint(5, faktor*45)
            zahl2 = random.randint(5, faktor*45)
            text = "{} + {} =" 
            variable = [str(zahl1), str(zahl2)]
            lsg = str(zahl1 + zahl2)
        else:
            rund1 = random.randint(0,faktor)
            zahl1 = random.randint(5,faktor*112)
            zahl1 = zahl1/10**rund1
            rund2 = random.randint(0,faktor)
            zahl2 = random.randint(5, faktor*112)
            zahl2 = zahl2/10**rund2
            text = "{} + {} =" 
            variable = [format_zahl(zahl1,rund1), format_zahl(zahl2,rund2)]
            lsg = f"{format_zahl(zahl1+zahl2,max(rund1,rund2))}"
        return typ, typ2, titel, text, "", text.replace(" ",""), variable, "", "", [lsg], 0, zahl1+zahl2, {'name':'normal'}

def subtrahieren(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "":
        typ_anf = 1 
        typ_end = 3
        if stufe >= 6 or jg >= 7 or "mit" in optionen:
            typ_end = 5 + stufe%2                               #6 für E-Kurs
        return typ_anf, typ_end
    else:
        typ = random.randint(typ_anf, typ_end)
        typ2 = 0 
        hilfe_id = 0
        pro_text = einheit = anmerkung = ""
        faktor = stufe%2+1                                  #2 für E-Kurs, 1 für G-Kurs und i
        if typ_end >3:
            typ = random.randint(typ_anf, typ_end+1)
    # hier wird die Aufgabe erstellt:
        if typ == 1:                                                #ganze Zahlen
            zahl2 = random.randint(1, 99)
            erg = random.randint(1, 49)
            zahl1 = erg+zahl2
            text = frage = "{} - {} ="
            variable = [str(zahl1), str(zahl2)]
            hilfe_id = 1
            lsg = str(erg)
            titel = "Subtrahieren"
        elif typ == 2:                                              #ganze Zahlen
            exp = random.randint(2,4)
            zahl2 = 10**exp
            zahl1 = random.randint(1,zahl2-1)
            # text = pro_text = f"ergänze {zahl1} zu {zahl2}"
            text = pro_text = "ergänze {} zu {}"
            variable = [str(zahl1),str(zahl2)]
            frage = "{1}-{0}="
            erg = zahl2 - zahl1
            lsg = str(erg)
            titel = "Ergänzen"
        elif typ == 3:                                              #Wechselgeld
            NOTES = [200, 500, 1000, 2000, 5000, 10000]
            einkauf = random.randint(5, 5950)
            start = 0
            while True:
                if NOTES[start] > einkauf:
                    break
                start += 1
            gegeben = (random.choice(NOTES[start:]))
            if gegeben != 200:
                art = "Schein"
            else:
                art = "Stück"
            kleingeld = int(einkauf%100)
            text = "Du hast für {}€ eingekauft und bezahlst mit einem {}€ {}" 
            pro_text = "Wechselgeld: {1}"
            if kleingeld > 0 and random.random()>0.5:
                if kleingeld > 50:
                    kleingeld -=50
                else:
                    if random.random()<0.3:
                        if kleingeld%10 in (1, 4, 9):
                            kleingeld += 1
                            anmerkung = "Achtung du hattest keine 1ct Münzen mehr!"
                if art == "Schein":
                    typ2 = 1
                    text = text + " und {}ct in Münzen".format(kleingeld) 
                    #pro_text = pro_text + "+" + format_zahl(kleingeld/100,2) 
                    pro_text = pro_text + "+{3}"
                else:
                    art = ""
                    text = text + " und {}ct".format(kleingeld) 
                erg = round((gegeben - einkauf + kleingeld)/100,2)
                hilfe_id = 3                
            else:
                erg = round((gegeben - einkauf)/100,2)        
            text = text + ".<br> Wieviel Wechselgeld erhälst du?"
            #pro_text = pro_text  + "-" + format_zahl(einkauf,2) + "€"
            pro_text = pro_text  + "-{0}€"
            variable = [format_zahl(einkauf/100,2),format_zahl(gegeben/100,0),art,format_zahl(kleingeld/100,2)]
            frage = "Wechselgeld="
            einheit = "€"
            lsg = f"{format_zahl(erg)}€"
            titel = "Wechselgeld"
        elif typ == 4:                                              #Kommazahlen
            rund1 = random.randint(0,1)
            zahl2 = random.randint(1, 99)
            zahl2 = zahl2/10**rund1
            rund2 = random.randint(0,1)
            erg = random.randint(1, 99)
            erg = erg/10**rund2
            zahl1 = zahl2+erg
            text = frage = "{} - {} ="
            variable = [format_zahl(zahl1,max(rund1,rund2),False), format_zahl(zahl2,rund1,False)]
            lsg =   f"{format_zahl(erg,max(rund1,rund2),False)}"
            titel = "Subtrahieren"
        else:                                                       #Zahlen kleiner 0
            if typ == 5:
                exp = random.randint(0, 2)
                zahl2 = 10**(-1*exp)
                zahl1 = random.randint(1,9)*zahl2/10
                exp2 = 1
            else:
                exp = random.randint(0, 1)
                zahl2 = 10**(-1*exp)
                zahl1 = random.randint(1,99)*zahl2/100
                exp2 = 2
            text = pro_text = "ergänze {} zu {}"
            variable = [format_zahl(zahl1, exp+exp2,),format_zahl(zahl2, exp)]
            frage = "{1}-{0}="
            erg = zahl2 - zahl1
            lsg = f"{format_zahl(zahl2-zahl1,exp+exp2)}"
            titel = "Ergänzen"
        return typ, typ2, titel, text, pro_text, frage, variable, einheit, anmerkung, [lsg],  hilfe_id, erg, {'name':'normal'}

def verdoppeln(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "":
        typ_anf = 0
        typ_end = 3
        if stufe >= 6 or jg >= 7 or "mit" in optionen:
            typ_anf = -2
            typ_end = 2
        return typ_anf, typ_end
    else:
        typ = random.randint(typ_anf, typ_end)
        typ2 = 0
        titel = "Verdoppeln"
        hilfe_id = 1
    # hier wird die Aufgabe erstellt:
        if typ > 0:
            zahl1 = random.randint(6,60)
            text = "Was ist das Doppelte von {}?"
            frage = "{}{}2=?"
            variable = [str(zahl1), chr(8901)]
            lsg = str(zahl1*2) 
            erg = zahl1*2      
        elif typ == 0:
            zahl1 = random.randint(3,30)
            text = "Was ist das <u>Vierfache</u> von {}?"
            frage = "{}{}4=?"
            variable = [str(zahl1), chr(8901)]
            lsg = str(zahl1*4)  
            erg = zahl1*4      
            hilfe_id = 2
        else:                                                               #Kommazahlen      
            zahl2 = random.randint(4,60)
            zahl1 = zahl2*10**(typ)
            text = "Was ist das Doppelte von {}?"
            frage = "{}{}2=?"
            variable = [format_zahl(zahl1,abs(typ)), chr(8901)]
            lsg = f"{format_zahl(zahl1*2,abs(typ))}" 
            erg = zahl1*2    
    return typ, typ2, titel, text, "", frage, variable, "", "", [lsg], hilfe_id, erg, {'name':'normal'}
    
def halbieren(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "":
        typ_anf = 1
        typ_end = 1
        if stufe >= 6 or jg >= 7 or "mit" in optionen:
            typ_anf = 2
            typ_end = 2 + stufe%2
        return typ_anf, typ_end
    else:
        typ = random.randint(typ_anf, typ_end)
        typ2 = 0
        titel = "Halbieren"
    # hier wird die Aufgabe erstellt:
    # hier wird die Aufgabe erstellt:
        if typ == 1:
            zahl1 = random.randint(5,99)
            text = "Was ist die Hälfte von {}?"
            variable = [(str(2*zahl1))]
            erg=zahl1
            lsg = str(zahl1)       
        elif typ > 2:                                                               #Kommazahlen      
            zahl2 = random.randint(0,2)
            zahl1= 2*random.randint(1,99)
            zahl1 = zahl1/10**(zahl2)
            text = "Was ist die Hälfte von {}?"
            variable = [format_zahl(zahl1,zahl2)]
            erg=zahl1/2
            lsg = f"{format_zahl(zahl1/2,zahl2)}"   
        else:   
            zahl2 = random.randint(0,2)
            zahl3= random.randint(1,99)
            zahl1 = zahl3/10**(zahl2)
            text = "Was ist die Hälfte von {}?"
            variable = [format_zahl(zahl1,zahl2)]
            erg=zahl1/2
            lsg = f"{format_zahl(zahl1/2,(zahl2+(zahl3%2)))}"
        frage = "{}:2"  
    return typ, typ2, titel, text, "", frage, variable, "", "", [lsg], 0, erg, {'name':'normal'}

def einmaleins(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "":
        typ_anf = 1
        typ_end = 11
        if "nur" in optionen:
            typ_end = 7
        return typ_anf, typ_end
    else:
        typ = random.randint(typ_anf, typ_end)
        typ2 = 0
        titel = "1 mal 1"
        anmerkung = ""
    # hier wird die Aufgabe erstellt:
        if typ <= 7 :
            zahl1 = random.randint(2,10)
            zahl2 = random.randint(2,10)
        elif typ < 10:                                                               #Kommazahlen      
            zahl1 = random.randint(4,14)
            zahl2 = random.randint(2,10) 
        else:   
            zahl1 = random.randint(10,13)
            zahl2 = random.randint(10,13)
        if typ in (6,7,10):
            variable = [str(zahl1*zahl2), ":", str(zahl2)]
            anmerkung = "Achtung - Division!"
            lsg = str(zahl1)  
            erg = zahl1  
        else:
            variable = [str(zahl1), chr(8901), str(zahl2)]
            lsg = str(zahl1*zahl2)  
            erg = zahl1*zahl2  
        text = "{} {} {} ="
    return typ, typ2, titel, text, "", text.replace(" ",""), variable, "", anmerkung, [lsg], 0, erg, {'name':'normal'}

def kopfrechnen(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "":
        typ_anf = 1
        typ_end = 9
        if "nur" in optionen:
            typ_end = 7
        return typ_anf, typ_end
    else:
        typ = random.randint(typ_anf, typ_end)
        typ2 = 0
        titel = "Kopfrechnen"
        hilfe_id = 1
    # hier wird die Aufgabe erstellt:
        if typ < 3 or typ == 6 :                                        # Plus
            zahl1 = random.randint(1,99)
            zahl2 = random.randint(1,9)
            lsg = str(zahl1+zahl2)
            erg = zahl1+zahl2
            if typ < 3:
                variable = [str(zahl1), "+", str(zahl2)]
            else:
                variable = [str(zahl2), "+", str(zahl1)]
        elif typ == 3  or typ == 7:                                     # Minus
            zahl2 = random.randint(1,9)
            zahl1 = random.randint(1,90) + zahl2
            lsg = str(zahl1-zahl2)
            erg = zahl1-zahl2
            variable = [str(zahl1), "-", str(zahl2)]
        elif typ == 4:                                                  # Multiplikation
            zahl1 = random.randint(1,10)
            zahl2 = random.randint(1,10)  
            variable = [str(zahl1), chr(8901), str(zahl2)]
            lsg = str(zahl1*zahl2)  
            erg = zahl1*zahl2  
        elif typ == 5:                                                  # Division
            zahl2 = random.randint(2,9)
            zahl1 = random.randint(1,9) * zahl2
            erg = zahl1/zahl2
            lsg = str(erg)
            variable = [str(zahl1), ":", str(zahl2)]
        else:
            zahl1 = random.randint(1,14)
            if zahl1 < 5:
                zahl2 = random.randint(1,4+zahl1) + (11-zahl1)   
            else:
                zahl2 = random.randint(1,14)
            typ2 = random.randint(1,5)
            if typ2 == 5:
                lsg = str(zahl2)
                erg = zahl1
                variable = [str(zahl1*zahl2), ":", str(zahl2)]                 
            else:
                lsg = str(zahl1*zahl2)
                erg = zahl1*zahl2
                variable = [str(zahl1), chr(8901), str(zahl2)]  
        text = "{} {} {} ="
    return typ, typ2, titel, text, "", text.replace(" ",""), variable, "", "", [lsg], hilfe_id, erg, {'name':'normal'}

class MathFormatter(string.Formatter):
    def format_field(self, value, format_spec):
        """ floats are formatted with comma.
        There is a special format specifier for division with remainder.
        {:r} only output there is a remainder
        {:<d>r} output the remainder for division with <d> (e.g. {:15r}).
        {:<d>c} output the number as a fraction with divisor <d>.
        """
        if format_spec.endswith(('r', 'c')):
            result = format(int(value), 'd')
            if value % 1:
                if format_spec == 'r':
                    result += " + Rest"
                else:
                    divisor = int(format_spec[:-1])
                    rest = round((value % 1) * divisor)
                    if format_spec.endswith('r'):
                        result += f" + Rest {rest:d}"
                    else:
                        result += f" + {rest:d}/{divisor:d}"
        else:
            result = format(value, format_spec)
            if format_spec.endswith('f') or isinstance(value, float):
                result = result.replace('.', ',')
        return result

    def evaluate(self, format_string, **kwargs):
        text = format_string.split('=')[0].format(**kwargs)
        return Parser().evaluate(text, {})

def sachaufgaben(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "":
        typ_anf = 1 
        typ_end = 3
        return typ_anf, typ_end
    elif eingabe != "":
        if typ == 21 and int(eingabe) == int(lsg[1]):
            return -1, "Das ist ein Pfosten zu wenig! Zeichne doch mal eine Skizze!"
        else:
            return -1, "" 
    else:
        titel = "Sachaufgaben"
        typ = typ_anf 
        # kommt von main      
        #pro_text = ""
        #anmerkung = ""
        hilfe_id = 0
        #einheit = ""
        sachaufgaben = Sachaufgabe.objects
        max = sachaufgaben.aggregate(Max('lfd_nr'))['lfd_nr__max']
        if typ > max:
            typ = 1   
        aufgabe = Sachaufgabe.objects.get(lfd_nr = typ)
        while aufgabe.ab_jg > jg:
            typ +=1
            if typ > max:
                typ = 1                  
            aufgabe = Sachaufgabe.objects.get(lfd_nr = typ)
        text = aufgabe.text
        aufgabe = Sachaufgabe.objects.get(lfd_nr = typ)
        text=aufgabe.text
        pro_text=aufgabe.pro_text
        loesung=aufgabe.loesung
        frage = aufgabe.links_text
        einheit = aufgabe.rechts_text
        variablen_auswahl=aufgabe.variable
        variablen = {
            name: random.choice(werte)
            for name, werte in variablen_auswahl.items()
        }
        formatter = MathFormatter()
        text = (formatter.format(text, **variablen))
        ergebnis = formatter.evaluate(loesung, **variablen)
        if "r" in loesung.split("=")[1] or ":.0f" in loesung.split("=")[1]:
            ergebnis=ergebnis//1
        lsg = [(formatter.format(loesung, ergebnis, **variablen))]
        if aufgabe.anmerkung:
            anmerkung=aufgabe.anmerkung
            if "indiv" in anmerkung:
                lsg.append(str(ergebnis-1))
                lsg.append("indiv_0")
                anmerkung=""              
        else:
            anmerkung=""
        return typ, typ2, titel, text, pro_text, frage, variablen, einheit, anmerkung, lsg,  hilfe_id, ergebnis, {'name':'normal'}

def zahl_wort(zahl):
    einer = ["", "ein", "zwei", "drei", "vier", "fünf", "sechs", "sieben", "acht", "neun", "zehn", "elf", "zwölf", "dreizehn", "vierzehn", "fünfzehn", "sechzehn", "siebzehn", "achtzehn", "neunzehn", "zwanzig"]
    zehner = ["zwanzig", "dreißig", "vierzig", "fünfzig", "sechzig", "siebzig", "achtzig", "neunzig"]
    if zahl > 99:
        zahl_hundert = zahl//100
        zahlwort = einer[zahl_hundert] + "hundert"
        zahl = zahl%100
    else:
        zahlwort = ""
    if zahl <= 20:
        zahlwort = zahlwort + einer[zahl]
    else:
        zahl_einer = zahl%10
        zahlwort = zahlwort + einer[zahl_einer]
        zahl_zehner = zahl//10
        if zahl_einer != 0:
            zahlwort = zahlwort + "und" + zehner[zahl_zehner-2]
        else:
            zahlwort = zahlwort + zehner[zahl_zehner-2]
    return zahlwort

def ggt(a,b):
    if b == 0:
        return a
    return ggt(b, a % b)

def lcm(a,b):
  return (a * b) // math.gcd(a,b)

def trenner(wert):
    zahl_mill = wert//1000000        
    zahl_tsnd = wert%1000000//1000
    zahl_klein = wert%1000 
    zahl = ""
    zahl =  "%d %03d %03d"%(zahl_mill, zahl_tsnd, zahl_klein)
    zahl = zahl.lstrip("0").lstrip(" ").lstrip("0").lstrip(" ").lstrip("0")  
    return zahl

def zahlen(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "":                                                              #hier wird typ_anf und typ_end festgelegt u.u. nach Wahl unter 'Optionen'
        typ_anf = 1
        if stufe >= 6 or jg >= 7 or "Kommazahlen" in optionen:
            typ_end = 9
        elif stufe >= 10 or jg >= 7 or "Brüchen" in optionen:
            typ_end = 10
        elif stufe >= 20 or jg >= 8 or "negativen" in optionen:
            typ_end = 12
        else:
            typ_end = 5        
        return typ_anf, typ_end
    elif eingabe != "":
        if typ ==10 and not "/" in eingabe:
            return 0, "Du sollst den angezeigten Wert als Bruch eingeben!"
        else:
            return 0, "" 
    else:                                                                           # hier wird die Aufgabe erstellt:
        typ = random.randint(typ_anf, typ_end+stufe%2)
        typ2 = 0 
        hilfe_id = 0
        anm = ""
        pro_text = ""    
        parameter = {'name':'normal'}
        if typ == 1:                                                                 #Zahlen schreiben
            titel = "Zahlen schreiben"
            exponent = random.randint(5,7+stufe%2)
            zahl1 = random.randint(10000,10**exponent)
            if stufe%2 == 1:
                while not "0" in str(zahl1):
                    zahl1 = random.randint(10000,10**exponent)
            if zahl1 >= 1000000:
                zahl_mill = zahl1//1000000
                if zahl_mill == 1:
                    text = "Eine Million "
                else: 
                    text = (zahl_wort(zahl_mill)).title() + "millionen " 
            else:
                text =""
            zahl_tsnd = zahl1%1000000//1000
            text =text + zahl_wort(zahl_tsnd).title() + "tausend<wbr>"
            zahl_klein = zahl1%1000
            text_k = text + zahl_wort(zahl_klein)
            text = "Schreibe folgende Zahl in Ziffern: {}"
            frage = "Als Zahl:"
            variable = [text_k]
            lsg = [trenner(zahl1)]
            erg=zahl1
        elif typ == 2:                                                               #Vorgänger Nachfolger
            titel = "Vorgänger und Nachfolger"
            typ2 = random.randint(1,2)
            zahl3 = random.randint(2,3+stufe%2)
            zahl1 = 1
            for n in range(1,zahl3):
               zahl2 = random.randint(0,3)
               zahl2 = (20-zahl2)%10
               zahl1 = zahl1 + zahl2*10**n
            if typ2 == 1:
                text = "Wie heißt der Nachfolger von {}?" 
                frage = "Nachfolger="
                variable = [str(zahl1)]
                erg = zahl1+1
                lsg = str(zahl1+1)
                hilfe_id = 1
            else:
                if zahl1 < 1:
                    zahl1 = 1
                text = "Wie heißt der Vorgänger von {}?" 
                frage = "Vorgänger="
                variable = [str(zahl1)]
                erg = zahl1-1
                lsg = str(zahl1-1)
                hilfe_id = 2
        elif typ in (3,6,7,8):                                                       #kleiner größer gleich
            titel = "Kleiner, größer oder gleich"
            zuza1 = random.randint(1,9)
            zuza2 = 1
            if typ == 3:
                stellen = random.randint(2,3)
            else:
                stellen = random.randint(1,2)
            zahl1 = zahl2 = zuza1*10**stellen
            zuza = [0, zuza1, zuza2]
            for n in 0, stellen-1:
                random.shuffle(zuza)
                zahl1 = zuza[0] * 10**n + zahl1
                zahl1_str = str(zahl1)
                random.shuffle(zuza)
                zahl2 = zuza[0] * 10**n + zahl2  
                zahl2_str = str(zahl2)
            if typ in [6,8]:                                      #erzeugt Kommazahlen
                komma = random.randint(0,2)
                if komma > 0:
                    zahl1_str = str(zahl1)[:komma]+","+str(zahl1)[1:].rstrip("0")
                    zahl2_str = str(zahl2)[:komma]+","+str(zahl2)[1:].rstrip("0")
                else:
                    zahl1_str = "0,"+str(zahl1).rstrip("0")
                    zahl2_str = "0,"+str(zahl2).rstrip("0")
                zahl1_str = zahl1_str.rstrip(",")
                zahl2_str = zahl2_str.rstrip(",") 
                zahl1=float(zahl1_str.replace(",", "."))
                zahl2 = float(zahl2_str.replace(",", "."))
            if typ in [7,8]:                                      #erzeugt negative Zahlen
                zahl1_str = "-" + str(zahl1_str)
                zahl2_str = "-" + str(zahl2_str)
                zahl1 = -zahl1
                zahl2 = -zahl2
            pro_text = "{} ? {}"
            text = 'Kleiner, größer oder gleich?<br>' + pro_text 
            frage = ""
            variable = [zahl1_str, zahl2_str]
            anm = "(Setze das entsprechende Zeichen ein)" 
            erg = None
            if zahl1 < zahl2:
                lsg = [str(zahl1) + "<" +  str(zahl2), "<"]
            elif zahl1 > zahl2:
                lsg = [str(zahl1) + ">" +  str(zahl2), ">"]
            else:
                lsg = [str(zahl1) + "=" +  str(zahl2), "="]
            parameter = {'name':'normal'}                  
        else:                                                                        # 4+5 ganze zahlen, 9+12 Kommazahlen, 10 Brüche, 11+12 negative Zahlen
            titel = "Zahlenstrahl"
            if typ != 10:
                bruch = False
                if typ == 4 and stufe%2 == 1:
                    eint = 20                       # 10 = 10er, 20 = 5er, 25 = 4er (für Brüche)
                else:
                    eint = 10
                exp = random.randint(1,4)
                z = 10**exp                         #Einteilung der Anzeige 0.1 1, 10, 100 ...
                if typ > 10:
                    v = random.randint(3,7)*-1
                else:
                    v = random.randint(0,8)         #ist die schieb des Nullpunktes
                if typ_end == 5 and v == 0:         #ohne neg Zahlen bei 20 an, sonst bei 0
                    anf = 20                             
                else:
                    anf = 0
                text_v = len(str(z))*-3             #die Verscheibung des Textes (dmit die Zahl in der Mitte unter dem Strich steht)
                if stufe%2 == 1 and eint == 10 and z > 10:
                    zahl1 = random.randint(1,90)*5
                else:
                    zahl1 = random.randint(1,45)*10
                text = "Auf welche Zahl zeigt der Pfeil{} ?"
                variable = [""]               
                if eint == 10 and zahl1%10 == 5:
                    anm = "(Du musst genau hinsehen: Der Pfeil steht zwischen zwei Strichen.)"
                frage = "Die Zahl heißt:"
                erg = int((zahl1+v*100)*z/100)
                lsg = str(erg)
            else:
                bruch = True
                typ2 = random.randint(1,4)
                anf = 0
                z = 1
                v = 0
                text_v = 0
                nenner_liste = [4,5,10]
                random.shuffle(nenner_liste)
                nenner = nenner_liste[0]
                if nenner == 4:
                    eint = 25
                else:
                    eint = 10
                zaehler = nenner
                while zaehler%nenner == 0:                      #keine ganzen Zahlen
                    zaehler = random.randint(1,nenner)
                bruch = 0.0
                if typ2 > 2:
                    ganz = 0
                else:
                    ganz = typ2
                bruch = zaehler/nenner+ganz
                zahl1 = bruch * 100
                hilfe_id = 3
                erg = None
                ganz = int(bruch*100//100)
                #zaehler = int(bruch*100//eint)
                zaehler = int(bruch*100//eint - ganz * 100/eint)
                nenner = int(100/eint) 
                bruch_str = str(zaehler) + "/" + str(nenner) 
                if ganz == 0:
                    lsg = [bruch_str]
                else:
                    bruch_str = str(ganz) + " " + bruch_str
                    lsg = [bruch_str, (str(zaehler+ganz*nenner)+"/"+str(nenner))] 
                kuerz = ggt(zaehler,100/eint)
                if kuerz > 1 :
                    bruch_str = str(int(zaehler/kuerz)) + "/" + str(int(nenner/kuerz)) 
                    if ganz == 0:                        
                        lsg.append(bruch_str)
                    else: 
                        bruch_str = str(ganz) + " " +  bruch_str
                        lsg.append(bruch_str)
                        lsg.append(str(int((zaehler+ganz*nenner)/kuerz)) +"/"+ str(int(nenner/kuerz)))
                lsg = lsg + ["indiv_0"]
                text = "Welcher Bruch ist hier dargestellt{} ?"
                frage = "Der Bruch heißt:"
                variable = [""]
                anm = "Schreibe als Bruch (7/9) oder als gemischte Zahl (1 2/7)"
            parameter = {'name': 'svg/zahlenstrahl.svg', 'anf': anf, 'eint':eint, 'v': v, 'txt0':  z+(v-1)*z, 'txt1': z+v*z, 'txt2': z+(v+1)*z, 'txt3': z+z*(v+2), 'txt4': z+z*(v+3), 'text_v': text_v, 'x': int(zahl1)+20, 'bruch':bruch}
        return typ, typ2, titel, text, pro_text, frage, variable, "", anm, lsg, hilfe_id, erg, parameter 

def malget10(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "":
        typ_anf = 1
        typ_end = 3
        if stufe >= 6 or jg >= 7 or "mit" in optionen:
            typ_end = 8 + stufe%2                               #6 für E-Kurs
        return typ_anf, typ_end
    else:
        typ = random.randint(typ_anf, typ_end)
        typ2 = 0
        hilfe_id = 0
        #variable = []
        exp = random.randint(1,3)
        #Zahlen erstellen:
        if typ < 4:                                     #Ergebnis ganze Zahl
            zahl1 = random.randint(1,99)                #Multi.
            zahl2 = 10**exp 
            if typ == 3:                                #Div.'                    
                exp2 = 0
                while exp2 < exp:
                    exp2 = random.randint(1,3)
                zahl1 = zahl1 * 10**exp2
            if typ < 3:
                hilfe_id = 1 
                if stufe%2 == 0:
                    hilfe_id = 2 
            else:
                hilfe_id = 3 
                if stufe%2 == 0:
                    hilfe_id = 4 
        #Ergebnis Kommazahl:
        elif typ == 4:                                  #Ganz mal Komma
            zahl1 = random.randint(1,999)/10  
            zahl2 = 10**exp 
            hilfe_id = 5
        elif typ == 5:                                  #Ganz Mal Komma 
            zahl1 = random.randint(1,99)    
            zahl2=  10**(exp*-1) 
            hilfe_id = 6
        elif typ == 6:                                  #Komma Mal Komma 
            zahl1 = random.randint(1,999)/10    
            zahl2=  10**(exp*-1)
            hilfe_id = 6                                    
        elif typ == 7:                                  #Ganz / Ganz
            zahl1 = random.randint(1,99)  
            zahl2 = 10**exp 
            hilfe_id = 7
        elif typ == 8:                                  #Ganz / Komma
            zahl1 = random.randint(1,99)  
            zahl2=  10**(exp*-1) 
            hilfe_id = 8                                   
        else:                                           #Div. durch Kommazahl  typ 9                           
            zahl1 = random.randint(1,999)/10    
            zahl2 = 10**(exp*-1) 
            hilfe_id = 9 
        #Aufgabe, Ergebnis, Lösung, Hilfe:    
        if typ == 1 or typ == 2 or typ == 4 or typ == 5 or typ == 6:    #Multiplikation: typ 1,2, 4, 5, 6
            text = "Multipliziere:<br> {} {} {}="
            variable = [str(zahl1).replace(".", ","), chr(8901), str(zahl2).replace(".", ","), exp]
            erg = zahl1 * zahl2
            lsg = str(int(erg))
            if typ < 5:
                titel = "Mal: 10, 100, 1000"
            else:
                titel = "Mal: 0,01; 0,1"
        else:                                           #Division: typ 3, 6, 7 , 8, 9
            text = "Dividiere:<br> {} {} {}="
            variable = [str(zahl1).replace(".", ","), ":", str(zahl2).replace(".", ","), exp]
            erg = zahl1 / zahl2
            lsg = str(round(erg,5)).replace(".", ",").rstrip(",")
            if typ == 3 or typ == 7:
                titel = "Geteilt durch: 10, 100, 1000"
            else:
                titel = "Geteilt durch: 0,1; 0,01" 
        return typ, typ2, titel, text, "", "{}{}{}", variable, "", "", [lsg], hilfe_id, erg, {'name':'normal'}

def runden(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "":
        typ_anf = 1
        typ_end = 6
        if stufe >= 6 or jg >= 7 or "mit" in optionen:
            typ_anf = -3  
        return typ_anf, typ_end
    elif eingabe != "":
        loe = (lsg[0])
        if eingabe.replace(" ","") != loe.replace(" ",""):
            erg = loe.replace(",",".")
            eing = eingabe.replace(",",".")
            if float(erg) == float(eing):
                meldung = "Leider falsch! Richtig wäre: " + (erg) + "- Deine Eingabe: " + eing + "<br>Du darfst die Null am Ende nicht weglassen - <br>Die Zahl muss genau {0} Stellen hinter dem Komma haben".format(len(erg)-erg.find("."))
                return -1, meldung.replace(".", ",")
        else:
            return 0, "" 
    else:
        typ = random.randint(typ_anf, typ_end)
        typ2 = 0
        titel = "Runden"
        name_liste = ("Einer", "zehn", "hundert", "tausend", "zehntausend", "hunderttausend",  "million")
        n = ""
        if typ < -1:
            endung = "stel" 
        elif typ == 6:
            endung = "en"
        elif typ > 0:
            endung = "er"
            n = "n"
        elif typ == -1:
            endung = "tel"
        else:
            endung = ""
        if typ > 0:
            exp = 10**(typ+2)
            zahl1 = int(random.random()*exp)  
            name = name_liste[typ] + endung
            name = name.title()
            zahl = trenner(zahl1).lstrip("0")
            text = " Runde {} auf {}"
            variable = [str(zahl), name, typ+1, n]
            erg = round(zahl1 / 10.0 ** typ)
            erg = int(erg * 10 ** typ)
            lsg = [trenner(erg)]
            hilfe_id = 1 
            next = name_liste[typ-1]
            if stufe%2 == 0:
                hilfe_id = 2

        else:
            zahl2 = random.randint(1,2)
            zahl1 = int(random.random()*10**(abs(typ)+zahl2+1))
            zahl1 = zahl1*10**(typ-zahl2)
            zahl = format_zahl(zahl1,abs(typ)+zahl2)
            name = name_liste[abs(typ)] + endung
            name = name.title()
            text = " Runde {} auf {}"
            variable = [str(zahl).replace(".", ","), name, abs(typ), n]
            if typ < 0:
                erg = round(zahl1 ,abs(typ))
                lsg = ["{0:.{1}f}".format(zahl1,abs(typ)).replace(".",",")]
                hilfe_id = 3
                if stufe%2 == 0:
                    hilfe_id = 4
            else:
                lsg = [format_zahl(zahl1,abs(typ))]
                hilfe_id = 5
                if stufe%2 == 0:
                    hilfe_id = 6
                if typ == 0:
                    hilfe_id = 0   
            lsg = lsg + ["indiv"]
        erg = None
        frage = "{}".format(*variable) + chr(8776)
        return typ, typ2, titel, text, "", frage, variable, "", "", lsg, hilfe_id, erg, {'name':'normal'}

def regeln(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "":
        typ_anf = 1
        typ_end = 15 + stufe%2
        return typ_anf, typ_end
    else:
        typ = random.randint(typ_anf, typ_end) 
        typ2 = 0
        erg = None
        anmerkung = ""
        hilfe_id = 0
        if typ < 5:
            operation_liste = ["Addition", "Subtraktion", "Multiplikation","Division"]
            name_liste = ["Plus", "Minus", "Mal", "Geteilt"]
            ergebnis_liste = ["Summe", "Differenz", "Produkt", "Quotient"]
            typ2 = random.randint(0,3)
        elif typ > 10:
            titel = "Zahlenfolgen"
            folge = []
            n = 1
            zahl = random.randint(1,2)
            anzab = random.randint(0,1)	
            anz = 4
        else:
            titel = "Rechenregeln"
            hilfe_id = 1
        if typ < 3:                                         # begriffe
            titel = "Begriffe"
            text = "Wie heißt das Ergebnis einer {}saufgabe?"
            frage = "Das Ergebnis heißt:"
            variable = [operation_liste[typ2], ", ".join(ergebnis_liste), operation_liste[typ2], name_liste[typ2]]
            erg = None
            anmerkung = "Achte auf die korrekte Schreibweise!"
            lsg = ergebnis_liste[typ2]
            random.shuffle(ergebnis_liste)
            hilfe_id = 2
            if stufe%2 == 0:
                hilfe_id = 3 
        elif typ < 5:                                       # Begriffe
            titel = "Kennst du die Begriffe?"
            artikel_liste = ["die", "die", "das", "den"]
            endung_liste = ["","","","en"]
            if typ2 == 0:
                zahl1 = random.randint(1,1000)
                zahl2 = random.randint(1,20)
                erg = zahl1 + zahl2
            elif typ2 == 1:
                zahl3 = random.randint(1,980)
                zahl2 = random.randint(1,20)
                zahl1 = zahl3 + zahl2
                erg = zahl3    
            elif typ2 == 2:
                zahl1 = random.randint(1,12)
                zahl2 = random.randint(1,15)
                erg = zahl1 * zahl2 
            else:
                zahl3 = random.randint(1,9)
                zahl2 = random.randint(1,9)
                zahl1 = zahl3 * zahl2
                erg = zahl3                                            
            text = "Berechne {0} {1}{2} aus {3} und {4}"
            if typ2 == 3:
                frage = "Der {1} beträgt"
            else:
                frage = "{} {} beträgt"
            variable = [artikel_liste[typ2], ergebnis_liste[typ2], endung_liste[typ2], str(zahl1), str(zahl2), ergebnis_liste[typ2], operation_liste[typ2]]
            #lsg = str(erg)
            if stufe%2 == 0:
                hilfe_id = 4 
        elif typ == 5:                                      # Rechenregeln * +
            zahl1=random.randint(1,10)
            zahl2=random.randint(1,8)
            zahl3=random.randint(1,7)
            text = "{} · ({} + {})="
            variable = [str(zahl1), str(zahl2), str(zahl3)]
            erg=zahl1*(zahl2+zahl3)
        elif typ == 6:                                      # Rechenregeln ( + )+( + )
            zahl1=random.randint(1,8)
            zahl2=random.randint(1,7)
            zahl3=random.randint(1,8)
            zahl4=random.randint(1,7)
            text="({} + {}) · ({} + {})="
            variable = [str(zahl1), str(zahl2), str(zahl3), str(zahl4)]
            erg=(zahl1+zahl2)*(zahl3+zahl4)
        elif typ == 7:                                      # Rechenregeln + :
            zahl1=random.randint(2,4)
            zahl2=random.randint(1,10)
            zahl3=random.randint(1,10)*zahl1
            text= "{} + {} : {}="
            variable = [str(zahl2), str(zahl3), str(zahl1)]
            erg=zahl2+zahl3/zahl1
        elif typ == 8:                                      # Rechenreglen * -
            erg = 0
            while erg <= 0:
                zahl1=random.randint(2,10)
                zahl2=random.randint(1,5)*zahl1
                zahl3=random.randint(2,5)
                erg=zahl2*zahl3-zahl1
            text= "{} · {} - {}="
            variable = [str(zahl2), str(zahl3), str(zahl1)]
        elif typ == 9:                                      # Rechenregeln + *
            zahl1=random.randint(1,10)
            zahl2=random.randint(1,10)
            zahl3=random.randint(1,10)
            text= "{} + {} · {}="
            variable = [str(zahl1), str(zahl2), str(zahl3)]
            erg=zahl1+zahl2*zahl3
        elif typ == 10:                                     # Rechenregeln * +
            zahl1=random.randint(1,10)
            zahl2=random.randint(1,10)
            zahl3=random.randint(1,10)
            text="{} · {} + {}="
            variable = [str(zahl1), str(zahl2), str(zahl3)]
            erg=zahl1*zahl2+zahl3
        else:                                               # Folgen
            if typ == 11:
                hilfe_id = 5
                add = random.randint(2,4)	    
                mult = random.randint(2,3)	
                zahl = random.randint(2,10)     #Startzahl
                anzab = random.randint(0,2)	    #Start Anzeige                
            elif typ == 12:
                hilfe_id = 6
                add = random.randint(2,4)	    
                mult = random.randint(2,3)	
            elif typ == 13:
                hilfe_id = 7
                add = random.randint(3,5)       #wird subtrahiert	    
                mult = random.randint(1,2)	             
            elif typ == 14:
                hilfe_id = 8
                anmerkung = "Hier musst du zwei verschiedene Rechnungen anwenden."
                add = random.randint(2,4)	    
                mult = random.randint(2,3)
                if mult == 3 and anzab == 1:
                    anz = 3	
            elif typ == 15:
                hilfe_id = 9
                mult = random.randint(2,3)	                  
                add = mult
                while add >= mult:
                    add = random.randint(1,2)	#wird addiert
                zahl1 = 2
                anzab = 1
            elif typ == 16:                                     # Fibonacci
                folge = ["0","1"]
                a = 1 
                b = 1
                anmerkung = "Diese Folge nennt man 'Fibonacci Zahlen'."
                hilfe_id = 10
                anzab = 0           
            if anzab == 0:
                zahl = 1
            if typ >12:
                anz = anzab + 6
            if typ == 16:
                anz =random.randint(5,8)
            n = 1
            while n <= anz + anzab:
                folge.append(str(zahl))
                if typ == 11:
                    zahl = zahl + add
                elif typ == 12:
                    zahl = zahl * mult
                elif typ == 13:
                    if n%2 == 1:
                        zahl = zahl + add
                    else:
                        zahl = zahl - mult                   
                elif typ == 14:
                    if n%2 == 1:
                        zahl = zahl * mult
                    else:
                        zahl = zahl + add
                elif typ == 15:
                    if n%2 == 1:
                        zahl = zahl * mult
                    else:
                        zahl = zahl - add                        
                else:
                    zahl = a + b
                    b = a
                    a = zahl
                n = n+1
        if typ > 10:
            folge.append("...")   
            if anzab > 0:
                folge = folge[anzab:n+anzab]  
                folge = ["..."] + folge        
            text = "Wie heißt die nächste Zahl: <br>{}?"
            variable = ["; ".join(folge)]
            lsg = str(zahl)
        elif typ >= 3:
            lsg = str(erg)
        if typ >= 11:
            frage = "Die nächste Zahl heißt:"
        elif typ >= 5:
            frage = text.replace(" ", "")
        return typ, typ2, titel, text, "", frage, variable, "", anmerkung, [lsg], hilfe_id, erg, {'name':'normal'}

#die drei folgenden Funktionen werden aus 'Geometrie' und aus 'Figuren' aufgerufen und erstellt Grafiken von Figuren:
def sub_figuren():
    box_hoehe=350
    box_breite = 400
    parameter = {'object': 'viereck'}
    schieb_x3 = schieb_x4 = schieb_y3 = schieb_y4  = 0
    typ2 = random.randint(1,6)
    if typ2 == 1:                                                           #Rechteck
        anmerkung = "(4 rechte Winkel, je 2 gegenüberliegende Seiten gleich lang)"
        lsg = ["Rechteck"]
        seiten = ["a", "b", "a", "b"]
        breite = random.randint(15,35)*10
        hoehe = breite
        while abs(breite-hoehe) <50:
            hoehe = random.randint(15,25)*10
    elif typ2 == 2:                                                         #Quadrat
        anmerkung = "(4 rechte Winkel, alle Seiten gleich lang)"
        lsg = ["Quadrat"]
        seiten = ["a", "a", "a", "a"]
        schieb1 = schieb2 = 0
        breite = hoehe = random.randint(15,30)*10
    elif typ2 == 3:                                                         #Parallelogramm
        anmerkung = "(je 2 gegenüberliegende Seiten sind parallel und gleich lang)"
        lsg = ["Parallelogramm"]
        seiten = ["a", "b", "a", "b"]
        breite = random.randint(15,35)*10
        hoehe = breite
        while abs(breite-hoehe) <50:
            hoehe = random.randint(15,25)*10
        while abs(schieb_x3) < 20:
            schieb_x3 = random.randint(-15,15)*10
        schieb_x4 = schieb_x3
    elif typ2 == 4:                                                         #Trapez
        anmerkung = "(nur 2 gegenüberliegende Seiten sind parallel)"
        lsg = ["Trapez"]
        seiten = ["a", "b", "c", "d"]
        schieb = 0 
        while abs(schieb) < 20 or breite+schieb < 40 or hoehe+schieb < 40 or max(breite, breite+schieb) >300 or max(hoehe, hoehe+schieb) >300:
            schieb = random.randint(-15,5)*8
            breite = random.randint(25,35)*8
            hoehe = random.randint(15,20)*8
        typ3 = random.randint(1,4)
        if typ3 == 1:
            schieb_x3 = schieb
        elif typ3 == 2:
            schieb_x4 = schieb
        elif typ3 == 3:
            schieb_y3 = schieb
        else:
            schieb_y4 = schieb
        x0 = int((box_breite-max(breite+schieb_x3, breite+schieb_x4))/2)
        y0 = int((box_hoehe-max(hoehe+schieb_y3, hoehe+schieb_y4))/2)
        if schieb_x4 == 0:
            x1 = x0
        else:
            x1 = x0 + abs(schieb_x4)
        x2 = x0 + breite
        x3 = x2 + schieb_x3
        x4 = x1 + schieb_x4
        y1 = y2 = box_hoehe - y0
        y3 = y1 - hoehe - schieb_y3
        y4 = y1 - hoehe - schieb_y4
        ecken_x = [-5,-5,-5,-5]                             #schieb Benennung in x
        ecken_y = [25,25,-10,-10]                           #schieb Benennung in y
    elif typ2 == 5:                                                         #Raute
        anmerkung = "(alle Seiten gleich lang, je 2 sind parallel)"
        lsg = ["Raute", "Rhombus"]
        seiten = ["a", "a", "a", "a"]                
        a = random.randint(25,33)*10
        breite = hoehe = 0
        while abs(breite-hoehe)<50:
            breite = int(a/2)+random.randint(-40,120)
            hoehe = pow(a**2-breite**2,0.5)
        y1 = y3 = int((box_hoehe)/2)
        y2 = y1 + int(hoehe/2)
        y4 = y1 - int(hoehe/2)                
        x2 = x4 = int((box_breite)/2)
        x1 = x2 - int(breite/2)
        x3 = x2 + int(breite/2)
        ecken_x = [-20,-5,10,-5]                          #schieb Benennung in x
        ecken_y = [5,25,5,-10]                            #schieb Benennung in y
    elif typ2 == 6:                                                         #Drache
        anmerkung = "(je 2 benachbarte Seiten sind gleich lang)"
        lsg = ["Drache", "Drachen", "Drachenviereck"]
        seiten = ["a", "a", "b", "b"]                
        breite =random.randint(10,14)*10
        hoehe = random.randint(8,16)*10
        schieb_y2 = random.randint(5,8)*10
        y1 = y3 = int((box_hoehe)/2 - schieb_y2/2)
        y2 = y1 + int(hoehe/2) + schieb_y2
        y4 = y1 - int(hoehe/2)                
        x2 = x4 = int((box_breite)/2)
        x1 = x2 - int(breite/2)
        x3 = x2 + int(breite/2)
        ecken_x = [-20,-5,10,-5]                          #schieb Benennung in x
        ecken_y = [5,25,5,-10]                            #schieb Benennung in y
    if typ2 < 4:
        x0 = int((box_breite-breite-(schieb_x3+schieb_x4)/2)/2)
        y0 = int((box_hoehe - hoehe+abs(schieb_y3+schieb_y4)/2)/2)
        x1 = x0
        x2 = x0+breite
        x3 = x2 + schieb_x3
        x4 = x1 + schieb_x4
        y1 = y2 = y0+hoehe
        y3 = y0 + schieb_y3
        y4 = y0 + schieb_y4
        ecken_x = [-5,-5,-5,-5]                             #schieb Benennung in x
        ecken_y = [25,25,-10,-10]                           #schieb Benennung in y
    xkoo = [x1, x2, x3, x4, x1]
    ykoo = [y1, y2, y3, y4, y1]
    ecken = ["A", "B", "C", "D"]
    seiten_x = [0,10,0,-20,0]                               #schieb Benennung in x
    seiten_y = [20,0,-10,0,10]                              #schieb Benennung in y
    parameter_2 = {'name': 'svg/geometrie.svg', 'box_hoehe': box_hoehe, 'box_breite': box_breite,
        'x1':x1, 'y1':y1,'x2':x2, 'y2':y2,'x3':x3, 'y3':y3,'x4':x4, 'y4':y4,
        'ecken': [
            (xkoo[n]+ecken_x[n], ykoo[n]+ecken_y[n], ecken[n]) for n in (range(0,4))
        ],
        'seiten': [
            ((xkoo[n]+xkoo[n+1])/2+seiten_x[n], (ykoo[n]+ykoo[n+1])/2+seiten_y[n], seiten[n]) for n in range(0,4)
            ],
    } 
    parameter.update(parameter_2)
    lsg = lsg + ["indiv_0"] 
    return typ2, anmerkung, lsg, parameter

def dreieck(typ2):
    if typ2 == 1:
        x1 = random.randint(4,12)
        y1 = random.randint(1,12) 
    else:
        x1 = random.randint(-3,8)
        y1 = random.randint(-3,8) 
    breite = random.randint(2,6)
    hoehe = random.randint(2,6)        
    return x1, y1, breite, hoehe    

def sub_dreiecke(typ):
    box_hoehe = 350
    box_breite = 600 
    anmerkung =""
    x1 = 100
    y0 = 30
    winkel = ""
    rotate = ""
    if typ == 10 or typ == 7:                                               #Benennung von Dreiecken
        #typ=5
        typ2 = random.randint(1,5)
        if typ2 == 1:                                                         #gleichschenkliges Dreieck
            pro_text = "Dreieck mit zwei gleich langen Seiten?"
            lsg = ["gleichschenkliges Dreieck","gleichschenkliges", "gleichschenklig"]
            seiten = ["c", "a", "a"]
            breite = random.randint(150, 250)
            seite = breite                
            while abs(seite-breite) < 40:
                seite = random.randint(150,250)
                hoehe = int((seite**2-(int(breite/2))**2)**0.5)
            x2 = x1 + breite
            x3 = x1 + int(breite/2)
            y1 = y2 = y0 + hoehe
            y3 = y0
        if typ2 == 2:                                                         #gleichseitiges Dreieck
            pro_text = "Dreieck mit drei Seiten gleich langen Seiten?"
            lsg = ["gleichseitiges Dreieck","gleichseitiges", "gleichseitig"]
            seiten = ["a", "a", "a"]
            breite = random.randint(150, 250)
            seite = breite
            hoehe =int((seite**2-(int(breite/2))**2)**0.5)
            x2 = x1 + breite
            x3 = x1 + int(breite/2)
            y1 = y2 = y0 + hoehe
            y3 = y0
        if typ2 == 3:                                                         #rechtwinkliges Dreieck
            pro_text = "Dreieck mit einem 90° Winkel?"
            lsg = ["rechtwinkliges Dreieck","rechtwinkliges", "rechtwinklig"]
            seiten = ["c", "b", "a"]
            breite = random.randint(150, 250)
            hoehe = random.randint(100, 200)
            x2 = x1 + breite
            y3 = y0
            typ3 = random.randint(1,3)
            if typ3 == 1:
                x3 = x1 
                y1 = y2 = y0 + hoehe
                winkel = "A"
            if typ3 == 2:
                x3 = x1 + breite
                y1 = y2 = y0 + hoehe
                winkel = "B"
            if typ3 == 3:
                x2 = x1 + breite
                x3 = x1
                y2 = y0
                winkel = "C"
                rotate = int(math.atan(hoehe/breite) * 180 / math.pi)
            y1 = y0 + hoehe
        if typ2 == 4:                                                         #stumpfwinkliges Dreieck
            pro_text = "Dreieck, bei dem ein Winkel größer als 90° ist?"
            lsg = ["stumpfwinklges Dreieck","stumpfwinkliges", "stumpfwinklig"]
            seiten = ["c", "a", "b"]
            x0 = x1
            breite = random.randint(150, 250)
            hoehe = random.randint(150, 250)
            schieb = random.randint(20, 100)
            typ3 = random.randint(1,3)
            if typ3 == 1:
                x1 = x0 + schieb 
                x2 = x1 + breite
                x3 = x1 - schieb
            if typ3 == 2:
                x2 = x1 + breite
                x3 = x2 + schieb
            if typ3 == 3:
                diff = 0               
                while diff < 20000:
                    breite = random.randint(10, 200)
                    schieb = random.randint(10, 200)
                    hoehe = random.randint(80, 150)
                    a = int((breite**2+hoehe**2)**0.5)
                    b = int((schieb**2+hoehe**2)**0.5)
                    diff = (breite + schieb)**2 - (a**2 + b**2)
                x2 = x1 + breite + schieb
                x3 = x1 + schieb
            y1 = y2 = y0 + hoehe
            y3 = y0  
        if typ2 == 5:                                                         #spitzwinkliges Dreieck
            pro_text = "Dreieck, bei dem alle Winkel kleiner als 90° sind?"
            lsg = ["spitzwinkliges Dreieck","spitzwinkliges", "spitzwinklig"]
            seiten = ["c", "a", "b"]
            breite = random.randint(150, 250) 
            hoehe = random.randint(100, 200)
            schieb = breite
            while schieb +10 >= breite:
                schieb = random.randint(20, 100)
            x2 = x1 + breite
            x3 = x1 + schieb
            y1 = y2 = y0 + hoehe
            y3 = y0    
        text = "Wie nennt man so ein " + pro_text
        anmerkung = anmerkung + "<br>Achte auf die korrekte Schreibweise!"
        hilfe_id = 100
        frage = "So ein Dreieck heißt:"
        einheit = "Dreieck"
        ecken = ["A", "B", "C"]         
    else:                                                                   #Benennung von Ecken und Seiten'
        einheit = ""
        list_start = random.randint(0,2)
        seiten_liste = ["c", "a", "b", "c", "a", "b"]
        ecken_liste = ["A", "B", "C", "A", "B", "C"]
        seiten = seiten_liste[list_start:list_start + 3]
        ecken = ecken_liste[list_start:list_start + 3]
        typ3 = random.choice(ecken_liste[:3])                   #Auswahl der gesuchten/gegebenen Ecke
        typ4 = random.choice(seiten_liste[:3])                                             # """ Seite
        typ2 = random.randint(1,2)
        if typ2 == 1:                                           #Seite gesucht
            buchst = "x"
            artikel = "die"
            gesucht = "Seite"
            frage = "Sie heißt:"
            hilfe_id = 111
            ecken = [typ3 if x == typ3 else "" for x in ecken]
            seiten = ["x" if x == typ4 else "" for x in seiten] 
            lsg = [typ4]           
        else:                                                   #Ecke gesucht
            buchst = "X"
            artikel = "der"
            gesucht = "Eckpunkt"
            frage = "Er heißt:"
            hilfe_id = 112
            ecken = ["X" if x == typ3 else "" for x in ecken]
            seiten = [typ4 if x == typ4 else "" for x in seiten] 
            lsg = [typ3] 
        text = "Wie heißt {0} mit {1} gekennzeichnete {2} dieses Dreiecks?".format(artikel,buchst,gesucht)
        anmerkung = anmerkung + "<br>Achte auf Groß- und Kleinschreibung!</b>"
        breite = random.randint(150, 250) 
        hoehe = random.randint(100, 200)
        schieb = random.randint(20, 100)
        x2 = x1 + breite
        x3 = x1 + schieb
        y1 = y2 = y0 + hoehe
        y3 = y0      
    box_hoehe = hoehe + y0*2
    ecken_x = [-10,-2,-10]                           #schieb Benennung in x
    ecken_y = [25,25,-10]                            #schieb Benennung in y
    xkoo = [x1, x2, x3, x1]
    ykoo = [y1, y2, y3, y1]
    seiten_x = [-2,10,-20,0]                         #schieb Benennung in x
    seiten_y = [20,0,0,10]                           #schieb Benennung in y
    parameter = {'name': 'svg/geometrie.svg', 'object': 'dreieck', 'winkel': winkel, 'rotate': rotate, 'box_hoehe': box_hoehe, 'box_breite': box_breite, 'breite': breite,
        'x1':x1, 'y1':y1,'x2':x2, 'y2':y2,'x3':x3, 'y3':y3,
        'ecken': [
            (xkoo[n]+ecken_x[n], ykoo[n]+ecken_y[n], ecken[n]) for n in (range(0,3))
        ],
        'seiten': [
            ((xkoo[n]+xkoo[n+1])/2+seiten_x[n], (ykoo[n]+ykoo[n+1])/2+seiten_y[n], seiten[n]) for n in range(0,3)
            ],
    } 
    lsg = lsg + ["indiv_0"]    
    return typ2, text, frage, einheit, hilfe_id, anmerkung, lsg, parameter

#diese Funktion wird aus 'geometrie' und 'Körper' aufgerufen - aus "begriffe der Geometrie" mit jeweiligem jg - aus "Quader und Prismen" mit jg=-1 und Maßen:
def sub_koerper(jg, breite_u = 0, breite_o = 0, hoehe = 0, tiefe = 0, w = 0, box_hoehe = 350):
    box_breite = 400
    anmerkung =""
    hilfe_id = 50
    if jg == -1:
        typ2 = 6
        hilfe_id = 0
    elif jg > 9:
        typ2 = random.randint(1,8)
        hilfe_id = 51
    elif jg < 7:
        typ2 = random.randint(1,6)            
    else:
        typ2 = random.randint(1,5)
    if typ2 == 1 or typ2 == 2 or typ2 == 4 or typ2 == 6 or typ2 == 7:           #1 Quader, 2 Würfel, 4 Pyramide, 6Prisma, 7Pyramidenstumpf
        if jg == -1:
            parameter = {'object': 'prisma'}
        else:
            parameter = {'object': 'quader'}
            breite_u = random.randint(8,15)*5
        v = w = 0                                                               #v verschiebt die Ecken beim Pyramidenstumpf, w beim Prisma
        if typ2 == 1:                                                             # Quader
            lsg = ["Quader"]
            anmerkung = "Die Kanten sind <u>nicht</u> gleich lang"
            hoehe = tiefe = breite_u*2
            while breite_u*2 == hoehe == tiefe:
                hoehe = random.randint(10,15)*10
                tiefe = random.randint(10,30)*10
            breite_o = breite_u
        elif typ2 == 2:                                                           # Würfel'
            lsg = ["Würfel", "Kubus"]                                                  
            anmerkung = "Die Kanten sind gleich lang"
            hoehe = tiefe = breite_u*2
            breite_o = breite_u
        elif typ2 == 4:                                                           # Pyramide
            lsg = ["Pyramide"]
            anmerkung = ""
            hoehe = random.randint(10,15)*10
            tiefe = breite_u*2
            breite_o = 0
        elif typ2 == 6:                                                           # Prisma
            lsg = ["Prisma"]
            anmerkung = ""
            if jg != -1:                                                            # Das wird zur Berechnung aus Quader und Prismen aufgerufen
                breite_o = 0
                hoehe = random.randint(10,15)*10
                tiefe = random.randint(10,25)*10
                w = random.randint(-5,5)*10
        elif typ2 == 7:                                                           # Pyramidenstumpf
            lsg = ["Pyramidenstumpf"]
            anmerkung = ""
            hoehe = random.randint(10,15)*10
            tiefe = breite_u*2
            breite_o = breite_u - random.randint(15,20)
            v = int((breite_u - breite_o)/8)
            v = v*int(hoehe/65)
        box_hoehe = hoehe + (tiefe*0.4) + 10
        y0 = box_hoehe -5#-int((hoehe + int (tiefe*0.4))/2)
        x0 = int((box_breite - tiefe*0.35)/2)
        x11 = x0 - breite_u
        x12 = x0 + breite_u
        x13 = x0 + breite_o - v + w
        x14 = x0 - breite_o + v + w
        x21 = x11 + int(tiefe*0.35)
        x22 = x12 + int(tiefe*0.35)  
        x23 = x13 + int(tiefe*0.35)        
        x24 = x14 + int(tiefe*0.35)
        y11 = y12 = y0
        y13 = y14 = y11 - hoehe
        y21 = y22 = y11 - int(tiefe*0.35) 
        y23 = y24 = y21 - hoehe
        if typ2 == 6 and jg != -1:
            x23 = x23 - 2*v 
            x24 = x24 - 2*v  
            y13 = y13 - int(2.7*v)
            y14 = y14 - int(2.7*v)
            y23 = y23 + int(2.7*v) 
            y24 = y24 + int(2.7*v) 
        if jg == -1:
            box_hoehe = hoehe + tiefe*0.6 +20
        elif typ2 == 4:
            x13 = x14 = x23 = x24 = x0 + int(tiefe*0.175)
            y13 = y14 = y23 = y24 = y0 - hoehe - int(tiefe*0.35)                
        parameter_2 = {'name': 'svg/geometrie.svg', 'box_hoehe': box_hoehe, 'box_breite': box_breite,                
            'x11':x11, 'y11':y11,'x12':x12, 'y12':y12,'x13':x13, 'y13':y13,'x14':x14, 'y14':y14, 
            'x21':x21, 'y21':y21,'x22':x22, 'y22':y22,'x23':x23, 'y23':y23,'x24':x24, 'y24':y24,                    
        } 
        if jg == -1:                                                                # Koordinaten für Beschriftung der Pfeile'
            xmu = x11 + breite_u*0.75
            xmo = x24 + breite_o*0.75
            ym = y22 - hoehe*0.5
            parameter_3 = {'xmu': xmu, 'xmo': xmo, 'ym': ym}
            parameter_2.update(parameter_3)
    elif typ2 == 3 or typ2 == 5 or typ2 == 8:                                   #3 Zylinder, 5 Kegel, 8 Kegelstumpf
        parameter = {'object': 'zylinder'}
        anmerkung = ""
        x0 = int(box_breite/2) 
        rx_u = random.randint(4,8)*10
        ry_u = int(rx_u*0.3)
        x1 = x0 - rx_u
        x2 = x0 + rx_u
        hoehe = random.randint(8,15)*10
        box_hoehe = hoehe + 2*rx_u
        y0 = box_hoehe -rx_u#- int(hoehe/2)-ry_u 
        y1 = y0 
        y2 = y1 - hoehe
        if typ2 == 3:                                                             #Zylinder
            lsg = ["Zylinder"]
            rx_o = rx_u
            ry_o = int(rx_o*0.3)
            x4 = x1
            x3 = x2
        elif typ2 == 5:                                                           #Kegel
            lsg = ["Kegel"] 
            rx_o = 0
            ry_o = 0
            x3 = x0
            x4 = x0
        elif typ2 == 8:                                                           #Kegelstumpf
            lsg = ["Kegelstumpf"] 
            rx_o = rx_u - random.randint(20,30)
            ry_o = int(rx_o*0.3)
            x4 = x0 - rx_o
            x3 = x0 + rx_o  
        parameter_2 = {'name': 'svg/geometrie.svg', 'box_hoehe': box_hoehe, 'box_breite': box_breite,                 
            'rx_u': rx_u, 'ry_u': ry_u, 'x1': x1,'x2': x2, 'y1': y1, 'rx_o': rx_o, 'ry_o': ry_o, 'x3': x3,'x4': x4, 'y2': y2, 'x0': x0 }    
        anmerkung = anmerkung + "<br>Achte auf die korrekte Schreibweise!"
    lsg = lsg + ["indiv_0"]                                                 #sorgt dafür, dass die Eingabe nochmals in der Funktion der Aufgabe überprüft wird                             
    parameter.update(parameter_2)
    return typ2,  hilfe_id, anmerkung, lsg, parameter    

def geometrie(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "":                                                              #hier wird typ_anf und typ_end festgelegt u.u. nach Wahl unter 'Optionen'
        typ_anf = 1
        typ_end = 5
        if stufe >= 6 or jg >= 6  or "Dreiecke" in optionen: 
            typ_end = 11  
        elif stufe >= 6 or jg >= 6  or "Symetrie" in optionen: 
            typ_end = 8          
        elif stufe >= 6 or jg >= 6  or "Koordinaten" in optionen: 
            typ_end = 7  
        return typ_anf, typ_end
    elif eingabe != "":                                                             #hier werden die Eingaben überprüft wenn "iniv" in den Lösungen steht
        if typ == 7 or typ == 9:                                                    #Koordinaten
            if "(" not in eingabe or not ")" in eingabe:
                return 0, "Du musst die Koordinaten in Klammern eingeben!"
            elif not (";" in eingabe or "|" in eingabe) :
                return 0, "Du musst die Koordinaten mit ';' trennen!"        
            else:
                eingabe=eingabe.replace("(","").replace(")","").replace(",",".")
                if ";" in eingabe:
                    eingabe=eingabe.split(";")
                elif "|" in eingabe:
                    eingabe=eingabe.split("|")
                zahl=(float(eingabe[0])*10+20)*1000
                zahl = zahl + float(eingabe[1])*10
                if zahl == float(lsg[2]):
                    return 1, ""
            return 0, "" 
        elif typ == 10:
            if eingabe.upper() == lsg[0].upper():
                return 1, "" 
            else:
                return 0, "" 
        elif typ == 11:
            if eingabe.upper() == lsg[0].upper():
                return -1, "Achtung: Die Ecken werden mit Großbuchstaben beschriftet, die Seiten mit kleinen Buchstaben." 
            else:
                return 0, ""    
        elif typ in [2,3,5]:                                      #Groß- Kleinschreibung
            if eingabe.upper() == lsg[0].upper():
                return 0, "Achte auf Groß- und Kleinschreibung!" 
            if typ == 3: 
                if typ2 == 3:
                    if ("gram") in eingabe:
                        return 0, "Achte auf die Rechtschreibung!"
                return 0, ""
            elif typ == 5:                                                              #Körper
                if typ2 == 1:
                    if ("ader") in eingabe:
                        return 0, "Achte auf die Rechtschreibung!"
                elif typ2 == 3:
                    if ("inder") in eingabe:
                        return 0, "Achte auf die Rechtschreibung!"           
                elif typ2 == 5:
                    if ("amide") in eingabe:
                        return 0, "Achte auf die Rechtschreibung!"  
            return 0, ""     
        else:
            return 0, ""
    else:                                                                           # hier wird die Aufgabe erstellt:
        typ = random.randint(typ_anf, typ_end)
        box_hoehe = 370
        box_breite = 400
        pro_text = ""
        anmerkung =""
        erg = None 
        frage = ""
        einheit = "" 
        hilfe_id = 0 
        if typ == 1:                                                                #Parallel und Senkrechte
            lsg1 = ""
            n = 0
            erg = None
            winkel = [-40,-20, 0, 20, 40]
            start = random.randint(0,2) 
            typ2 = random.randint(1,4)
            if typ2 == 1:                                                           #g parallel
                g = winkel[start:]
                a = g[:2]  
                b = a[1:]           #gemeinsam
                g = a + b
                h = winkel[start:]
                h = h[:3]
            elif typ2 == 2:                                                         #h parallel
                h = winkel[start:]
                a = h[:2]  
                b = a[1:]
                h = a + b
                g = winkel[start:]
                g = g[:3]
            elif typ2 == 3:                                                         #Senkrechte
                start = random.randint(1,2)
                a = [winkel[start]]
                b = [winkel[start-1]]  
                g = a + b + b  
                b = [winkel[start+1]]    
                c = [winkel[start+2]]    
                h = a + b + c 
            else:                                                                   #Senkrechte
                start = random.randint(1,2)
                a = [winkel[start]]
                b = [winkel[start-1]]  
                h = a + b + b  
                b = [winkel[start+1]]    
                c = [winkel[start+2]]    
                g = a + b + c                 
            random.shuffle(g)
            random.shuffle(h)
            if typ2 == 1:
                while n < 3:
                    if g[n] == b[0]:
                        lsg1 = lsg1 + "g" + str(n+1)
                    n = n+1
            elif typ2 == 2:
                while n < 3:
                    if h[n] == b[0]:
                        lsg1 = lsg1 + "h" + str(n+1)
                    n = n+1
            else:
                while n < 3:
                    if g[n] == a[0]:
                        lsg1 = "g" + str(n+1)
                    n = n+1
                n = 0
                while n < 3:
                    if h[n] == a[0]:
                        lsg2 = "h" + str(n+1)
                    n = n+1
            if typ2 < 3:
                titel = "Parallele"
                text = "Welche der Geraden sind parallel zueinander?"
                hilfe_id= 11
                lsg = lsg1[:2] + " und " + lsg1[2:]
                lsg2= lsg1[2:] + lsg1[:2]
                lsg3 = lsg1[2:] + " und " + lsg1[:2]           
                lsg = [lsg, lsg1, lsg2, lsg3]
            else:
                titel = "Senkrechte"
                text = "Welche der Geraden sind senkrecht zueinander?"
                hilfe_id= 12
                lsg = lsg1 + " und " + lsg2
                lsg = [lsg] + [str(lsg1) + str(lsg2)]
                lsg = lsg + [str(lsg2) + str(lsg1)]
                lsg = lsg +  [lsg2 + " und " + lsg1]
            parameter = {'name': 'svg/parallele.svg', 'g11': g[0], 'g21':g[1], 'g31': g[2], 'g12': -g[0], 'g22': -g[1], 'g32': -g[2],
                        'h11': -h[0], 'h21': -h[1], 'h31': -h[2], 'h12': h[0], 'h22': h[1], 'h32': h[2]}
        elif typ == 2:                                                              #Begriffe: Strecke usw.
            liste = ["Strecke", "Gerade", "Halbgerade", "Strahl", "Streckenzug", "..."]
            hilfe_id = 20
            titel = "Grundformen der Geometrie"
            text = "Wie heißt diese Linie?"
            box_hoehe = 200
            typ2 = random.randint(1,4)
            if typ2 == 1:                                                           #Strecke
                anmerkung = "(Sie hat einen Anfang und ein Ende)"
                lsg = ["Strecke"]
                x = random.randint(20,100)
                parameter = {'object': 'strecke', "ende" : "12", 'x1': x, 'y1': 100, 'x2': 400-x, 'y2': 100}        
            elif typ2 == 2:                                                         #Gerade
                anmerkung = "(Sie hat keinen Anfang und kein Ende)"
                lsg = ["Gerade"]
                y = random.randint(-50,50)
                parameter = {'object': 'gerade', "ende" : "", 'x1': 0, 'y1': 100+y, 'x2': 400, 'y2': 100-y}
            elif typ2 == 3:                                                         #Gerade durch zwei Punkte
                pro_text = "text"
                text = "Durch zwei Punkte kann man immer eine Linie ziehen. <br>Wie nennt man so eine Linie in der Mathematik?"
                anmerkung = "(Sie hat keinen Anfang und kein Ende)"
                lsg = ["Gerade"]
                y = random.randint(-50,50)
                xkoo1 = random.randint(50,100)
                ykoo1= 100+y-int(xkoo1*y/200)
                xkoo2 = random.randint(250,300)
                ykoo2 = 100+y-int(xkoo2*y/200)
                parameter = {'object': 'gerade', "ende" : "", 'x1': 0, 'y1': 100+y, 'x2': 400, 'y2': 100-y, 'xkoo1': xkoo1, 'ykoo1': ykoo1, 'xkoo2': xkoo2, 'ykoo2': ykoo2}  
            elif typ2 == 4:                                                         #Strahl
                lsg = ["Strahl", "Halbgerade"]
                ende = str(random.randint(1,2))
                x = random.randint(50,100)
                if ende == "1":
                    x1 = x
                    x2 = 400
                    anmerkung = "(Sie hat einen Anfang und <u>kein</u> Ende)"
                else:
                    x1 = 0
                    x2 = 400-x 
                    anmerkung = "(Sie hat <u>keinen</u> Anfang und ein Ende)"                 
                parameter = {'object': 'strecke',"ende" : ende, 'x1': x1, 'y1': 100, 'x2': x2, 'y2': 100} 
            anmerkung = anmerkung + "<br>Achte auf die korrekte Schreibweise!"
            parameter_2 = {'name': 'svg/geometrie.svg', 'box_hoehe':box_hoehe, 'box_breite':box_breite}
            parameter.update(parameter_2)
            lsg = lsg + ["indiv_0"] 
        elif typ == 3:                                                              #Figuren
            liste = ["Rechteck", "Quadrat", "Parallelogramm", "Trapez", "Drachen", "Raute", "Rhombus", "allgemeines Viereck"]
            hilfe_id = 30
            titel = "Grundformen der Geometrie"
            text = "Wie heißt dieses Viereck?"
            anmerkung = anmerkung + "<br>Achte auf die korrekte Schreibweise!"
            typ2, anmerkung, lsg, parameter = sub_figuren()
        elif typ == 4:                                                              #A und u zusammengestzte Figuren
            titel = "Umfang und Fläche"  
            anmerkung = "Die kleinen Quadrate haben alle eine Seitenlänge von 1cm"
            hoehe = 70
            breite = 200
            typ3 = random.randint(1, 42)
            if typ3 == 1:
                schieb = [[0,1,1,0],[1,1,1,1],[1,1,1,1],[0,1,1,0]]
                umf = 16
                flae = 12
            elif typ3  == 2:
                schieb = [[1,0,0,1],[1,1,1,1],[1,1,1,1],[1,0,0,1]]
                umf = 20
                flae = 12	
            elif typ3 == 3:
                schieb = [[1,1,1,1],[1,0,0,1],[1,0,0,1],[1,1,1,1]]
                umf = 16+8
                flae = 12				
            else:
                hoehe = 80
                schieb = [[0,1,1,1,0],[1,1,1,1,1],[1,1,1,1,1],[1,1,1,1,1],[0,1,1,1,0]]
                umf = 20
                flae = 21
            typ2 = random.randint(1,2)
            if typ2 == 1:
                text = "Berechne den Umfang dieser Figur"
                erg = umf
                frage = "u="
                einheit = " cm "	
            else:
                text = "Berechne die Fläche dieser Figur"
                erg = flae 
                frage = "A="
                einheit = " cm² "
            lsg = [str(erg)]  
            schieb_positionen = [
                (x * 15, y * 15 - 15)
                for y, row in enumerate(schieb)
                for x, cell in enumerate(row)
                if cell
            ]
            parameter = {'name': 'svg/geometrie.svg', 'object': 'quadrat', 
                'box_hoehe' : hoehe+5,
                'box_breite' : 200, 
                'schieb': schieb_positionen,            
            }   
        elif typ == 5:                                                              #Körper
            titel = "Grundformen der Geometrie"
            text = "Wie heißt dieser Körper?"
            typ2,  hilfe_id, anmerkung, lsg, parameter = sub_koerper(jg)
        elif typ == 6:                                                              #räumliches Vorstellungsvermögen
            titel = "Räumliches Vorstellungsvermögen"
            text = "Ups, bei diesem Würfel sind ein paar Bausteine verlorengegegangen.<br>Wieviele sind es?"
            pro_text = "Wieviele Würfelchen fehlen?"
            anmerkung = "(Innen fehlen keine - nur an den Außenflächen - und natürlich auch nicht auf der Rückseite)"
            anzahl_breite = random.randint(3+stufe%2,5+stufe%2)
            anzahl_tiefe = anzahl_breite
            anzahl_hoehe = anzahl_breite
            second_last_plane = [
                [
                    (t == anzahl_tiefe - 1 and random.random() >= 0.75)
                    or (h == anzahl_breite - 1 and random.random() >= 0.75)
                    for h in range(anzahl_breite)
                ] for t in range(anzahl_tiefe)
            ]
            last_plane = [
                [
                    missing or random.random() >= 0.75
                    for missing in row
                ] for row in second_last_plane
            ]

            full_plane = [[False] * anzahl_breite] * anzahl_tiefe
            schieb_positionen = [
                (50 + h * 20 - t * 6, t * 6 - v * 20 + anzahl_hoehe*20 - 20)
                for v, plane in enumerate([full_plane] * (anzahl_hoehe - 2) + [second_last_plane, last_plane])
                for t, row in enumerate(plane)
                for h, missing in enumerate(row)
                if not missing
            ]
            soll = anzahl_breite * anzahl_tiefe * anzahl_hoehe
            erg = soll - len(schieb_positionen)
            lsg = [str(erg)]
                
            parameter = {'name': 'svg/geometrie.svg', 'object': 'raum',
                'box_hoehe' : anzahl_hoehe * 20 + anzahl_tiefe * 8,
                'box_breite' : 300,             
                'schieb': schieb_positionen,
            } 
        elif typ == 7:                                                              #Koordinaten
            titel = "Koordinatensystem"
            text = "Wie lauten die Koordinaten des Punktes A?"
            frage = "P="
            anmerkung="Du must die Koordinaten entweder so (  ;  ) oder so (  |  ) eingeben!"
            if stufe < 6:
                typ2 = 1
            elif stufe < 20:
                typ2 = 2
            else:
                typ2 = 3
            if typ2 ==1:                                                            #nur N im 1.Quadranten
                x_koo = random.randint(0,14)
                y_koo = random.randint(0,9) 
                lsg = ["({0};{1})".format(x_koo, y_koo)]
                lsg = lsg + ["({0}|{1})".format(x_koo, y_koo)]
                box_hoehe = 240
                box_breite = 350
                y_null = box_hoehe-40
                x_null = 30
                y_start = y_null
                x_start = 30
                einteilung = 20
                parameter_2 = {
                    'xvalues': [
                        (x_null + n*20, n) for n in range(0, 15)
                    ],
                    'yvalues': [
                        (y_null - n*20, n) for n in range(0, 10)
                    ],
                    'x_koo' : x_null + x_koo*20, 
                    'y_koo': y_null -(y_koo*20),
                    'text_a': "A",
                } 
            elif typ2 ==2:                                                          #nur Kommazahlen im 1.Quadranten
                x_koo = random.randint(0,20)
                y_koo = random.randint(0,20) 
                lsg = ["({0};{1})".format(x_koo/10, y_koo/10).replace(".", ",")]
                lsg = lsg + ["({0}|{1})".format(x_koo/10, y_koo/10).replace(".", ",")]
                box_hoehe = 280
                box_breite = 350
                y_null = box_hoehe-40
                x_null = 30
                y_start = y_null
                x_start = x_null
                einteilung = random.randint(1,2) * 10
                parameter_2 = {
                    'xvalues': [
                        (x_null + n*100, n) for n in range(0, 3)
                    ],
                    'yvalues': [
                        (y_null - n*100, n) for n in range(0, 3)
                    ],
                    'x_koo' : x_null + x_koo*10, 
                    'y_koo': y_null -(y_koo*10),
                    'text_a': "A",
                } 
            else:                                                                   #Koordinatensystem
                x_koo = random.randint(-12,22)
                y_koo = random.randint(-7,25) 
                lsg = ["({0};{1})".format(x_koo/10, y_koo/10).replace(".", ",")]
                lsg = lsg + ["({0}|{1})".format(x_koo/10, y_koo/10).replace(".", ",")]
                box_hoehe = 360
                box_breite = 400
                y_null = box_hoehe-100                  # y_Null entspricht der Lage der x-Achse
                x_null = 130                            # x_Null entspricht der lage der y-Achse
                y_start = box_hoehe                     # ist der Anfang der y-Achse
                x_start = 0                             # ist der Anfang der x-Achse
                einteilung = 10
                parameter_2 = {
                    'xvalues': [
                        (x_null + n*100, n) for n in range(-1, 5)
                    ],
                    'yvalues': [
                        (y_null - n*100, n) for n in range(0, 5)
                    ],
                    'x_koo' : x_null + x_koo*10, 
                    'y_koo': y_null -(y_koo*10),
                    'text_a': "A",
                }
            parameter = {'name': 'svg/koosys.svg', 'object': 'koordinaten',
                    'box_hoehe' : box_hoehe, 'box_breite' : box_breite,
                    'einteilung' :einteilung,
                    'y_null': y_null,'x_null': x_null,
                    'y_start': y_start,'x_start': x_start,
                    }
            parameter.update(parameter_2)                
            zahl=(x_koo+20)*1000+y_koo
            lsg = lsg + [str((x_koo+20)*1000+y_koo)]
            lsg = lsg + ["indiv_0"] 
        elif typ == 8:                                                              #Symmetrie
            titel = pro_text = "Symmetrie"
            zeichen_liste = [(0,1,2,3,4,5,6,7,8,9),      ("A", "B", "C", "D", "E", "F"),    ("G", "H", "I", "J", "K", "L"), ("M", "N", "O", "P", "Q", "R", "S"), ("T", "U", "V", "W", "X", "Y", "Z")]
            anzahl_achsen = [[ 7,              1,  2],   [  1,    5,                   0],  [  3,           1,     2],      [  5,         1,      1],            [1,    5,                     1]]
            erklaerung =    [[[1,2,4,5,6,7,9],[3],[0,8]],[["F"],["A","B","C","D","E"],[""]],[["G","J","L"],["K"],["H","I"]],[["N","P","Q","R","S"],["M"],["O"]], ["Z"],["T","U","V","W","Y"],["X"]]
            anzahl_punkt =  [2,                             0,                                 2,                              3,                                 2]
            erklaerung =    ["0 und 8",                     "",                                 "H und I",                        "N und S",                            "X und Z"]
            typ3 = random.randint(0,4)
            if typ3 == 0:
                auswahl = "Ziffern"
            else:
                auswahl = "Buchstaben"
            anzahl_frage = ["<u>keine</u>", "genau eine", "genau zwei", "vier"]
            typ5 = random.random()
            if typ5 < 0.6:
                typ4 = random.randint(0,2)
            else:
                typ4 = random.randint(0,3)
            if typ4 > 1:
                endung = "n"
            else:
                endung = ""  
            familie = "Die Familie der Vierecke umfasst: Rechteck, Quadrat, Parallelogramm, Trapez, Raute und Drache.<br>"
            familie_achsen =  [2,                          1,        2,                    1]
            erklaerung =     ["Parallelogramm und Trapez", "Drache", "Rechteck und Raute", "Quadrat"]
            if typ5 < 0.4:
                text = "Wieviele dieser {0} haben {1} Symetrieachse{2}?<br><br>{3}".format(auswahl, anzahl_frage[typ4], endung, zeichen_liste[typ3])
                erg = anzahl_achsen[typ3][typ4]
            elif typ5 < 0.6:
                text = "Wieviele dieser {0} sind punktsymetrisch?<br><br>{2}".format(auswahl,anzahl_frage[typ4],zeichen_liste[typ3])
                erg = anzahl_punkt[typ3]
            elif typ5 < 0.95:
                text = "{0}Wieviele dieser Vierecke besitzen {1} Symetrieachse{2}?".format(familie, anzahl_frage[typ4], endung)
                erg = familie_achsen[typ4]
            else:
                text = "{0}Wieviele dieser Vierecke sind punktsymetrisch?".format(familie)
                erg = 3
                erklaerung = ["Quadrat, Paralleogramm und Raute"]                
            parameter = {'name':'normal'}
            lsg = [str(erg)]   
        elif typ == 9:                                                              #Achsspiegelung
            titel = pro_text = "Achsspiegelung"
            erg = None
            if stufe < 20:
                typ2 = 1
            else:
                typ2 = 2
            if typ2 == 1:                                                           #nur positive Zahlen
                breite = 300 
                x_null = 30
                x_start = 30
                x_text_start = 0
                hoehe = 300                
                y_null = hoehe-40
                y_start = hoehe-40
                y_text_start = 0   
            else:                                                                   #auch negative Zahlen
                breite = 400
                x_null = 110
                x_start = 0
                x_text_start = -2
                hoehe = 400
                y_null = 280
                y_start = hoehe
                y_text_start = -2   
            x1 = d_breite = 1000                                                  
            y1 = d_hoehe =1000
            typ3 = random.randint(1,3)
            if typ3 == 1:                                                          #Spiegelachse ist Winkelhalbierende
                hilfe_id = 91
                x0 = 0
                y0 = 0
                #hier kommt das Dreieck:
                while x1 + d_breite > breite/20-3 or y1 + d_hoehe > hoehe/20-4  :
                    x1, y1, d_breite, d_hoehe = dreieck(typ2)
            elif typ3 == 2:                                                        #Spiegelachse parallel zur y-Achse
                x0 = random.randint(4,7)
                y0 = 0
                #hier kmmt das Dreieck:
                while x1 + d_breite > breite/20-3 or y1 + d_hoehe > hoehe/20-4 or x1 - x0 > x0 + x_null/20:
                    x1, y1, d_breite, d_hoehe = dreieck(typ2)
            elif typ3 == 3:                                                        #Spiegelachse parallel zur x-Achse
                x0 = 0
                y0 = random.randint(4,7)
                #hier kmmt das Dreieck:
                while x1 + d_breite > breite/20-3 or y1 + d_hoehe > hoehe/20-4 or y1 - y0 > y0 + y_null/20:
                    x1, y1, d_breite, d_hoehe = dreieck(typ2)
            x2 = x1 + d_breite
            y2 = y1
            y3 = y1 + d_hoehe
            x3 = x1 + random.randint(0,d_breite)
            #Berechnung der Bildpunkte
            if typ3 == 1:
                x1b = y1
                x2b = y2
                x3b = y3
                y1b = x1
                y2b = x2
                y3b = x3
            elif typ3 == 2:
                x1b = x1 - (x1 - x0)*2 
                x2b = x2 - (x2 - x0)*2 
                x3b = x3 - (x3 - x0)*2 
                y1b = y1
                y2b = y2
                y3b = y3
            elif typ3 == 3:
                x1b = x1  
                x2b = x2 
                x3b = x3 
                y1b = y1 - (y1 - y0)*2
                y2b = y2 - (y2 - y0)*2
                y3b = y3 - (y3 - y0)*2
            xb_liste = [x1b, x2b, x3b]
            yb_liste = [y1b, y2b, y3b]
            x_koo = [x1*20, x2*20, x3*20, x1*20]
            y_koo = [y1*20, y1*20, y3*20, y1*20]
            ecken = ["A", "B", "C"]
            ecken_x = [-20,10,-5]                               #schiebt Benennung in x
            ecken_y = [10,10,-10]                               #schiebt Benennung in y
            xb = -1
            while xb < 0:
                typ4 = random.randint(0,2)
                xb = xb_liste[typ4]
            yb = yb_liste[typ4] 
            text = "Das Dreieck ABC wird an der Spiegelachse S gespiegelt. <br>Wie lauten die Koordinaten des Punktes " + ecken[typ4] + "' des gespiegelten Dreiecks?"
            anmerkung="Du must die Koordinaten entweder so (  ;  ) oder so (  |  ) eingeben!"             
            lsg = ["({0};{1})".format(xb, yb)]
            lsg = lsg + ["({0}|{1})".format(xb, yb)]
            parameter = {
                'einteilung' :20,
                'box_hoehe' : hoehe,'box_breite' : breite,
                'hoehe' : hoehe,'breite' : breite,
                'y_null': y_null,'x_null': x_null,                
                'x_start': x_start,'y_start': y_start,
                'x0': x_null + x0*20,'y0': y_null - y0*20           
                }
            parameter_2 = {
                'name': 'svg/koosys.svg', 'object': 'spiegel', 'typ': typ3,
                'xvalues': [
                    (x_null + n*40, 2*n) for n in range(x_text_start, 7)
                ],
                'yvalues': [
                    (y_null - n*40, 2*n) for n in range(y_text_start, 7)
                ],                    
                'x1': x_null + x_koo[0], 'y1': y_null - y_koo[0], 
                'x2': x_null + x_koo[1], 'y2': y_null - y_koo[1], 
                'x3': x_null + x_koo[2], 'y3': y_null - y_koo[2],
                'ecken': [
                    (x_null+x_koo[n]+ecken_x[n], y_null-y_koo[n]+ecken_y[n], ecken[n]) for n in (range(0,3))
                ],  
                }
            parameter.update(parameter_2)
            zahl=(xb+20)*1000+yb
            lsg = lsg + [str((xb+20)*1000+yb)]
            lsg = lsg + ["indiv_0"] 
        else:                                                                       #10 Name Dreiecke - 11 Namen und Seiten Ecken
            titel = "Benennungen am Dreieck"
            typ2, text, frage, einheit, hilfe_id, anmerkung, lsg, parameter = sub_dreiecke(typ)     
        return typ, typ2, titel, text, pro_text, frage, [], einheit, anmerkung, lsg, hilfe_id, erg, parameter

def einheiten(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "": 
        typ_anf = 0
        typ_end = 4
        if stufe >= 12 or jg >= 7 or "Volumen" in optionen:
            typ_end = 6  
        elif stufe >= 4 or jg >= 6 or "Fläche" in optionen:
            typ_end = 5  
        if stufe >= 7 or jg >= 7 or "Komma" in optionen:
            typ_anf = -1
        return typ_anf, typ_end
    elif eingabe != "":                                                              #hier werden die Eingaben überprüft wenn "iniv" in den Lösungen steht
        if typ == 0:  
            if ":" not in eingabe:
                return 0, "Du musst die Stunden und Minuten mit einem Doppelpunkt trennen!"
            return 0, "" 
        if typ == 5:
            if eingabe.upper() == lsg[0].upper():
                return 0, "Achte auf Groß- und Kleinschreibung!" 
            return 0, "" 
    else:                                                                            #hier wird die Aufgabe erstellt:
        if typ_anf <0:                                                               #wenn typ_anf negativ werden Aufgaben mit Komma erstellt
            typ_anf = 0
            komma = True
        else:
            komma = False
        typ = random.randint(typ_anf, typ_end)                                      #welche Größe 1=Zeit 2=Masse 3=Länge 4=Fläche 5=Volumen negativ = mit Komma
        frage = "{}{}" + chr(8793)
        einheit = ""
        anmerkung = ""
        variable = []
        hilfe_id = 0
        endung = ""
        zahl1 = 0
        zuza = random.random()                                                       #kleiner oder größer?
        if zuza > 0.6:
            kleiner = 1                                     #eine Stelle kleiner'
        elif zuza > 0.2:
            kleiner = -1                                    #eine Stelle größer
        elif zuza > 0.1:
            kleiner = 2                                     #zwei Stelle kleiner'
        else:
            kleiner = -2                                    #zwei Stelle größer 
        if abs(kleiner) > 1:
            zahl1 = random.randint(1,20)
            if typ not in (3,4):                                    # Sprünge über eine Einheit nur bei Längen!
               kleiner = int(kleiner/2)
        else:
            zahl1 = random.randint(1,50)
        if komma:
            stelle = random.randint(-3,1)
            zahl1 = zahl1 * 10**stelle
        titel = "Einheiten umwandeln" 
        if typ ==0:                                         #Uhrzeit
            titel = "Uhrzeit"
            umwandlung = 0
            erg = None
            frage = ""
            einheit = ""
            h_digital = random.randint(1,24)
            min_list = [2,3,5,7,10,15]
            if random.random() < 0.9:
                halb = "halb"
            else:
                halb = ""
            if h_digital > 12:
                h = h_digital-12
            else:
                h = h_digital                 
            if random.random() <= 0.2:
                vornach = 'nach'
                if halb == 'halb':
                    min = random.choice(min_list[:4])                    
                else:    
                    min = min_digital = random.choice(min_list)
                if halb == 'halb':
                    h_digital -=1
                    min_digital = 30+min
            else:
                vornach = 'vor'
                h_digital -= 1 
                if halb == 'halb':
                    min = random.choice(min_list[:4])
                else:
                    min = random.choice(min_list[:5])
                if halb == 'halb':
                    min_digital = 30-min
                else:        
                    min_digital = 60-min  
            if h_digital < 12:
                tageszeit = 'morgens'
            elif h_digital < 14:
                tageszeit = 'mittags'
            elif h_digital < 18:
                tageszeit = 'nachmittags'
            elif h_digital < 22:
                tageszeit = 'abends'
            else:
                tageszeit = 'nachts'
            if h_digital == 0:
                stunde = 'Mitternacht'
            else:
                stunde = zahl_wort(h) + " Uhr"                
            if min == 15:
                min = 'um viertel'
            elif min == 30:
                min = "um halb"
                vornach = halb = ""
                if h_digital == 0:
                    h_digital = 23
                    min = "eine halbe Stunde vor "
                    tageszeit = ""
                else:
                    h_digital -=1
            else:
                min = "um " + zahl_wort(min) + " Minuten"    
            text = "Welche Uhrzeit zeigt eine Digitaluhr {} {} {} {} {}?".format(min,vornach,halb,stunde,tageszeit)
            lsg = [("{:02d}:{:02d}".format(h_digital,min_digital)),("{}:{:02d}".format(h_digital,min_digital)),"indiv_0"]
            anmerkung = "Trenne Stunden und Minuten mit einem Doppelpunkt - z.B. so '01:02'"
        elif typ == 1:                                      #Zeit
            einheiten_liste = ['sec', 'min', 'h', 'd']
            einheiten_namen = ['Sekunden', 'Minuten', 'Stunden', 'Tage']
            umwandlung = 60
            komma = False
        elif typ == 2:                                      #Massen
            einheiten_liste = ['mg', 'g', 'kg', 't']
            einheiten_namen = ['Milligramm', 'Gramm', 'Kilogramm', 'Tonnen']
            umwandlung = 3
        elif typ < 5:                                       #Längen
            einheiten_liste = ['mm', 'cm', 'dm', 'm', 'km']
            einheiten_namen = ['Millimeter', 'Zentimeter', 'Dezimeter', 'Meter', 'Kilometer']
            umwandlung = 1
        elif typ == 5:                                      #Flächen
            zuza = random.random()
            if zuza > 0.4:
                typ2 = 1
            elif zuza > 0.1:
                typ2 = 2
            else :
                typ2 = 3
            if typ2 == 1:
                umwandlung = 2
                einheiten_liste = ['mm²', 'cm²', 'dm²', 'm²']
                einheiten_namen = ['Quadratmillimeter', 'Quadratzentimeter', 'Quadratdezimeter', 'Quadratmeter']
            elif typ2 == 2:            
                umwandlung = 2
                zahl1 = 1
                einheiten_liste = ['m²', 'a', 'ha', 'km²']
                einheiten_namen = ['Quadratmeter', 'Ar', 'Hektar', 'Quadratkilometer'] 
            else: 
                umwandlung = -1
                erg = None
                typ4 = random.randint(1,2)
                frage = "Sie heißt:"
                if typ4 == 1:
                    pro_text = "eine Fläche von 10 mal 10 Metern hat eine eigene Bezeichnung - welche?"
                    text = "eine Fläche von 10 mal 10 Zentimetern nennt man auch 1 Quadratdezimeter (dm²).<br>Auch " + pro_text
                    lsg = ['Ar','a',"indiv_0"]   
                if typ4 == 2:
                    pro_text = "eine Fläche von 100 mal 100 Metern hat eine eigene Bezeichnung - welche?"
                    text = "eine Fläche von 1000 mal 1000 Metern nennt man auch 1 Quadratkilometer (km²).<br>Auch " + pro_text
                    lsg = ['Hektar','ha',"indiv_0"]             
        elif typ == 6:                                      #Volumen'
            umwandlung = 3
            zuza = random.random()
            if zuza > 0.7:
                typ2 = 1
            elif zuza > 0.5:
                typ2 = 2
            elif zuza > 0.2:
                typ2 = 3
            elif zuza > 0.1:
                typ2 = 4
            else :
                typ2 = 3
            if typ2 == 1:
                umwandlung = 3
                einheiten_liste = ['mm³', 'cm³', 'dm³', 'm³']
                einheiten_namen = ['Kubikmillimeter', 'Kubikzentimeter', 'Kubikdezimeter', 'Kubikmeter']
            elif typ2 == 2:
                umwandlung = 3
                einheiten_liste = ['ml', 'l', 'm³']
                einheiten_namen = ['Milliliter', 'Liter', 'Kubikmeter']  
            elif typ2 == 4:
                umwandlung = 0
                einheiten_liste = ['cm³', 'ml']
                einheiten_namen = ['Kubikzentimeter', 'Milliliter']    
            elif typ2 == 3 :
                umwandlung = 0
                einheiten_liste = ['dm³', 'l']
                einheiten_namen = ['Kubikdezimeter', 'Liter'] 
            else:
                umwandlung = -1
                pro_text = "<br>Wie nennt man einen Kubikdezimeter auch?"
                text = "eine Länge von 10 Zentimeter nennt man auch Dezimeter (dm), auch für den Kubikdezimeter (dm³) gibt es einen anderen Namen." + pro_text
                frage = "Er heißt auch:"
                erg = None
                lsg = ['Liter','l'] 
        if typ !=0 and umwandlung >= 0:                     #bei Fragen nach Bezeichnungen ist umwandlung -1
            text = "Wieviele {2} entsprechen {0} {3}{4}?"       
            if kleiner > 0:
                typ3 = random.randint(kleiner,len(einheiten_liste)-1)
            else:
                typ3 = random.randint(0,len(einheiten_liste)-1+kleiner)
            gegeben = einheiten_liste[typ3]
            gegeben_name = einheiten_namen[typ3]
            einheit = einheiten_liste[typ3-kleiner]
            einheit_name = einheiten_namen[typ3-kleiner]
            if typ == 3 or typ == 4:                        #Bei km Umwandlungszahl = 1000 und keine Sprünge zu dm
                if gegeben == "km":
                    kleiner = 1
                    umwandlung = 3
                    einheit = "m"
                    einheit_name = "Meter"
                elif kleiner < 0 and einheit == "km" :
                    kleiner = -1
                    umwandlung = 3
                    gegeben = "m"
                    gegeben_name = "Meter"
            if abs(kleiner) > 1:
                anmerkung = "Achtung: Zwischen {0} und {1} liegt noch die Einheit {2}!".format(gegeben, einheit,einheiten_liste[typ3-int(kleiner/2)])
            if umwandlung < 10:                             #bei Zeit bleibt der Faktor
                faktor = 10**(abs(umwandlung))              #ergänzt entsprechende Nullen
            else:
                faktor = umwandlung
            if abs(kleiner) == 2:
                faktor = faktor * faktor
            if zahl1 == 1:                                  #schwierige Umwandlungen nur mit 1
                if kleiner < 0:
                    zahl1 = zahl1 * faktor
            elif faktor == 60:
                zahl1 = int(random.choice(['1', '2','3','10']))
                if gegeben == "d" or einheit == "d":
                    faktor = 24
                if kleiner < 0:
                    zahl1 = zahl1 * faktor
                if zahl1 == 1:
                    gegeben_name = gegeben_name[:-1]
            else:
                if kleiner < 0:
                    zahl1 = zahl1 * faktor    
                    exp = random.randint(0,1)                           #ergänzt 0 bis 1 Nullen
                else:
                    exp = random.randint(0,2)                           #ergänzt 0 bis 2 Nullen
                zahl1 = zahl1*10**exp
            if "meter" in gegeben_name and zahl1 != 1:
                endung = "n"
            if komma:
                if kleiner > 0:
                    erg = zahl1 * faktor
                else:
                    erg = zahl1 / faktor
                if "." in str(zahl1):
                    zahl = f"{zahl1:.4f}".replace(".", ",").rstrip("0").rstrip(",")
                else:
                    zahl = f"{str(zahl1)}".replace(".", ",")
                variable = [str(zahl), gegeben, einheit_name, gegeben_name, endung, str(faktor)]
            else:
                variable = [str(zahl1), gegeben, einheit_name, gegeben_name, endung, str(faktor)]
                if kleiner > 0:
                    erg = zahl1 * faktor
                else:
                    erg = int(zahl1 / faktor)
            hilfe_id = 1 
            #hier fehlt noch die Hilfe für den G Kurs
            if abs(kleiner) > 1:
                hilfe_id = 3
            if faktor == 1:
                hilfe_id = 0
            lsg = [str(erg)+einheit]
        #lsg = lsg + ["indiv"]                              #sorgt dafür, dass die Eingabe nochmals in der Funktion der Aufgabe überprüft wird                             
        return typ, typ2, titel, text, "", frage, variable, einheit, anmerkung, lsg, hilfe_id, erg, {'name':'normal'}

def figuren(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "":                                                              #hier wird typ_anf und typ_end festgelegt u.u. nach Wahl unter 'Optionen'
        typ_anf = 2
        typ_end = 4
        if stufe >= 6 or jg >= 7 or "Dreieck" in optionen: 
            typ_anf = 1
            typ_end = 9 
        elif stufe >= 4 or jg >= 6 or "Parallelogramm" in optionen:
            typ_anf = 1
            typ_end = 5
        elif stufe >= 4 or jg >= 6 or "Seitenlänge" in optionen:
            typ_anf = 1
        return typ_anf, typ_end
    elif eingabe != "":                                                             #hier werden die Eingaben überprüft wenn "indiv" in den Lösungen steht
        loesung = (lsg[0])
        if typ == 1 or (typ >2 and typ < 8):
            if ("m") not in eingabe:
                return 0, "Du hast die Einheit vergessen!"
            loesung_getrennt=loesung.split()
            x_liste = ["c","d","m"]
            for x in x_liste:
                if x in eingabe:
                    eingabe_getrennt=eingabe.split(x,1)
                    eingabe_getrennt[1] = x + eingabe_getrennt[1]
                    break
            try:
                if float(eingabe_getrennt[0]) == float(loesung_getrennt[0]):
                    return 0.5, "<br>Die Zahl stimmt, die Einheit aber nicht - das ergibt einen halben Punkt Abzug! Richtig wäre: " + loesung_getrennt[1]
            except:
                return -1, ""
        if typ == 2 :                                                               #Groß- Kleinschreibung
            if eingabe.upper() == lsg[0].upper():                                   #Figuren
                return 0, "Achte auf Groß- und Kleinschreibung!"
            if (typ2 == 3 and ("gram") in eingabe) or typ2 == 4 and ("rape") in eingabe:
                return 0, "Achte auf die Rechtschreibung!"
        if typ == 7:                                                                #Benennung von Dreieckesarten
            if eingabe.upper() == lsg[1].upper():
                return 1, "" 
        if typ == 9:                                                                #Benennung von Ecken und Seiten
            if eingabe.upper() == lsg[0].upper():
                return -1, "Achtung: Die Ecken werden mit Großbuchstaben beschriftet, die Seiten mit kleinen Buchstaben." 
        else:
            return 0, ""
    else:                                                                           #hier wird die Aufgabe erstellt:
        typ = random.randint(typ_anf, typ_end)
        typ2 = 0
        pro_text = ""
        einheit = ""
        erg = None        
        hilfe_id = 0
        box_hoehe = 400
        box_breite = 600
        hoehe = 0
        titel = "Umfang und Fläche von Rechtecken" 
        einheiten_liste = ['mm', 'mm', 'cm', 'cm', 'dm', 'm']
        typ3 = random.randint(0, 5)
        einheit_aufg = einheiten_liste[typ3]
        zahl1 = random.randint(4, 12)
        zahl2 = random.randint(2, 11)
        if typ == 1:                                                            #Seite aus Fläche oder Umfang
            anmerkung = "Vergiss die Einheit nicht!"
            parameter = {'name':'normal'}
            typ2 = random.randint(1,5)
            if typ2 == 1:                                                       # a aus A
                frage = "a"
                gegeben1 = "A"
                zahl = zahl1*zahl2
                exp = "²"
                gegeben2 = "b"
                erg = zahl2
                hilfe_id=11
            elif typ2 == 2:                                                     # b aus A
                frage = "b"
                gegeben1 = "A"
                zahl = zahl1*zahl2
                exp = "²"
                gegeben2 = "a"
                erg = zahl2
                hilfe_id=12
            elif typ2 == 3:                                                     # a aus u
                frage = "a"
                gegeben1 = "u"
                zahl = 2*(zahl1+zahl2)
                exp = ""
                gegeben2 = "b" 
                erg = zahl2 
                hilfe_id=13
            elif typ2 == 4:                                                     # b aus u                                               
                frage = "b"
                gegeben1 = "u"
                zahl = 2*(zahl1+zahl2)
                exp = ""
                gegeben2 = "a" 
                erg = zahl2  
                hilfe_id=14 
            else:                                                               # a aus u Quadrat
                frage = "a"
                gegeben1 = "u"
                zahl = (zahl1*4)
                exp = ""
                gegeben2 = "" 
                erg = zahl1  
                hilfe_id=15
            if typ2 < 5:              
                text = "Berechne die Länge der Seite {0} eines Rechtecks mit:<br>{1}= {3}{5}{6} und {2}={4}{5}"
                pro_text = "{1}={3}{5}{6}, {2}={4}{5}, {0}=?"            
            else:
                text = "Berechne die Länge der Seite {0} eines Quadrates mit:<br>{1}= {3}{5}{6}"
                pro_text = "Quadrat: {1}={3}{5}{6}, {0}=?" 
            variable = [frage, gegeben1, gegeben2, zahl, zahl1, einheit_aufg, exp]
            frage = frage + "="
            lsg = ["{} {}".format(erg, einheit_aufg)]
        elif typ == 2:                                                          #Figuren benennen
            liste = ["Rechteck", "Quadrat", "Parallelogramm", "Trapez", "Drachen", "Raute", "Rhombus", "allgemeines Viereck"]
            hilfe_id = 20
            variable = []
            titel = "Grundformen der Geometrie"
            text = "Wie heißt dieses Viereck?"
            frage = "Das ist ein(e)"
            typ2, anmerkung, lsg, parameter = sub_figuren()
        elif typ == 3:                                                          #Fläche und Umfang von Rechtecken
            anmerkung = "Vergiss die Einheit nicht! (Anstelle von ² kannst du ^2 eintippen.)"
            figur = "Rechtecks"
            typ2 = random.randint(1,6)
            if typ2 < 3:                                #Fläche Rechteck
                gesucht = "die Fläche"
                erg = (zahl1*zahl2)
                exp ="²"
                frage = "A="
                hilfe_id = 31
            elif typ2 < 5:                              #Umfang Rechteck
                gesucht = "der Umfang"
                erg = 2*(zahl1+zahl2)
                exp = ""
                frage = "u=" 
                hilfe_id = 33  
            elif typ2 == 5:                             #Fläche Quadrat
                figur = "Quadrates"
                gesucht = "die Fläche"
                erg = (zahl1*zahl1)
                exp ="²"
                frage = "A="
                hilfe_id = 35
            elif typ2 == 6:                             #Umfang Quadrat
                figur = "Quadrates"
                gesucht = "der Umfang"
                erg = 4*zahl1
                exp = ""
                frage = "u=" 
                hilfe_id = 36
            variable = [str(zahl1), str(zahl2), einheit_aufg, exp, gesucht, figur]
            if typ2 < 5:
                text = "Berechne {4} eines {5} mit:<br>a={0}{2} und b={1}{2}"
                pro_text = "{5}: a={0}{2}, b={1}{2}, {4}=?" 
            else:
                text = "Berechne {4} eines {5} mit a={0}{2}"
                pro_text = "{5}: a={0}{2}, {4}=?" 
            lsg = ["{} {}{}".format(erg, einheit_aufg, exp)]
            parameter = {'name':'normal'}
        elif typ == 9:
            titel = "Benennungen am Dreieck"
            variable = []
            typ2, text, frage, einheit, hilfe_id, anmerkung, lsg, parameter = sub_dreiecke(typ)
        else:
        #elif typ == 4 or typ == 5 or typ == 6 or typ ==7:                      #Figuren mit Maßlinien typ2: 1 u Rechteck, 2 A Rechteck, 3 Parallelogramm, 4 Trapez, 5 und 6 Dreieck
            titel = "Umfang und Fläche von Figuren" 
            anmerkung = "Vergiss die Einheit nicht! <br>(Anstelle von ² kannst du ^2 eintippen.)"
            einheit_aufg = "mm"
            breite = zahl1
            hoehe = zahl2
            schieb = 0
            if typ == 4:                            # u und A von Rechteck und Quadrat
                typ2 = random.randint(1,2)
            elif typ == 5:                          # + Flache von Parallelogramm und Trapez
                typ2 = random.randint(1,4)
            else:                                   # + Dreicksfläche
                typ2 = random.randint(1,6)
            if typ2 == 1:                           # Umfang Rechteck
                figur = "Rechtecks"
                gesucht = "den Umfang"
                erg = 2*(zahl1+zahl2)
                exp =""
                frage = "u="
                hilfe_id = 10
                seiten = ["l="+str(breite)+"mm", "b="+str(hoehe)+"mm", "", ""]
                seiten_x = [0,10,0,0] 
                seiten_y = [20,0,0,0]
                x1 = x4 = int(box_breite/2-breite*10)
                x2 = x3 = x1 + breite*20
                y1 = y2 = int(box_hoehe/2+hoehe*10)
                y3 = y4 = y1 - hoehe*20
                xkoo = [x1, x2, x3, x4, x1]
                ykoo = [y1, y2, y3, y4, y1]
            else:                                   # Fläche
                gesucht = "die Fläche"
                exp ="²"
                frage = "A="
                if typ2 == 2:                       #Fläche Rechteck
                    figur = "Rechtecks"
                    erg = (zahl1*zahl2)
                    hilfe_id = 11
                    seiten = ["l="+str(breite)+"mm", "b="+str(hoehe)+"mm", "", ""]
                    seiten_x = [0,10,0,0] 
                    seiten_y = [20,0,0,0]
                    x1 = x4 = int(box_breite/2-breite*10)
                    x2 = x3 = x1 + breite*20
                    y1 = y2 = int(box_hoehe/2+hoehe*10)
                    y3 = y4 = y1 - hoehe*20
                    xkoo = [x1, x2, x3, x4, x1]
                    ykoo = [y1, y2, y3, y4, y1] 
                elif typ2 == 3:                     #Fläche Paralleogramm
                    schieb = 0
                    while schieb == 0:
                        schieb = random.randint(-3,3)
                    figur = "Paralleogramms"
                    seiten = ["g="+str(breite)+"mm", "", "", "h="+str(hoehe)+"mm"]
                    seiten_x = [0,0,0,20+abs(int(schieb*10))] 
                    seiten_y = [20,0,0,0]
                    x1 = int(box_breite/2-breite*10)
                    x2 = x1 + breite*20
                    x3 = x2 + schieb*20
                    x4 = x1 + schieb*20
                    y1 = y2 = int(box_hoehe/2+hoehe*10)
                    y3 = y4 = y1 - hoehe*20
                    xkoo = [x1, x2, x3, x4, x1]
                    ykoo = [y1, y2, y3, y4, y1]  
                    erg = (zahl1*zahl2)
                    #hilfe_id = 13
                elif typ2 == 4:                     #Fläche Trapez
                    schieb = random.randint(2,zahl1-1)
                    while ((2*breite-schieb)*hoehe/2)%1 != 0:                        
                        schieb = random.randint(2,zahl1-1)

                    figur = "Trapezes"
                    seiten = ["g1="+str(breite)+"mm", "", "g2="+str(breite-abs(schieb))+"mm", "h="+str(hoehe)+"mm"]
                    seiten_x = [0,0,0,20] 
                    seiten_y = [20,10,-10,10]
                    x1 = int(box_breite/2-breite*10)
                    x2 = x3 = x1 + breite*20
                    typ3 = random.randint(0,schieb)
                    x4 = x1 + typ3*20
                    x3 = x4 + breite*20 - abs(schieb)*20
                    y1 = y2 = int(box_hoehe/2+hoehe*10)
                    y3 = y4 = y1 - hoehe*20
                    xkoo = [x1, x2, x3, x4, x1]
                    ykoo = [y1, y2, y3, y4, y1]  
                    erg = int((2*zahl1-schieb)*hoehe/2)
                else:                               #Fläche Dreieck
                    schieb = random.randint(0,breite)
                    while ((breite*hoehe)/2)%1 != 0:
                        breite = random.randint(4, 12)
                        hoehe = random.randint(2, 11)
                        schieb = random.randint(0,breite)
                    figur = "Dreiecks"
                    seiten = ["g="+str(breite)+"mm", "h="+str(hoehe)+"mm", "", ""]
                    seiten_x = [0,10,0,0] 
                    seiten_y = [20,0,0,0]
                    x1 = int(box_breite/2-breite*10)
                    x2 = x1 + breite*20
                    x3 = x4 = x1 + schieb*20
                    y1 = y2 = int(box_hoehe/2+hoehe*10)
                    y3 = y4 = y1 - hoehe*20
                    xkoo = [x1, x3, x3, x3, x1]
                    ykoo = [y1, y2, y3, y4, y1]  
                    erg = int((breite*hoehe)/2)
                    hilfe_id = 12
            variable = [str(zahl1), str(zahl2), str(schieb), einheit_aufg, exp, gesucht, figur]
            text = "Berechne {5} dieses {6}" 
            pro_text = "{6}: a={0}{3}, b={1}{3}, {5}=?"  
            lsg = ["{} {}{}".format(erg, einheit_aufg, exp)]
            parameter = {'name': 'svg/geometrie.svg', 'object': 'figur', 'box_hoehe': box_hoehe, 'box_breite': box_breite, 'hoehe': hoehe*20,
                    'x1':x1, 'y1':y1,'x2':x2, 'y2':y2,'x3':x3, 'y3':y3,'x4':x4, 'y4':y4,
                    'seiten': [
                    (int((xkoo[n]+xkoo[n+1])/2+seiten_x[n]), int((ykoo[n]+ykoo[n+1])/2+seiten_y[n]), seiten[n]) for n in range(0,4)
                    ]}

        lsg = lsg + ["indiv_0"]                              #sorgt dafür, dass die Eingabe nochmals in der Funktion der Aufgabe überprüft wird     
        return typ, typ2, titel, text, pro_text, frage, variable, einheit, anmerkung, lsg, hilfe_id, None, parameter

def kommazahlen(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "":                                                               
        typ_anf = 1
        typ_end = 6
        if stufe >= 6 or jg >= 6 or "Multiplikation" in optionen:
            typ_end = 8
        if stufe >= 6 or jg >= 6 or "Divison" in optionen:
            typ_end = 10
        return typ_anf, typ_end
    else:                                                                            
        typ = random.randint(typ_anf, typ_end)
        typ2 = 0
        titel = "Rechnen mit Dezimalzahlen" 
        text = "default{}"
        pro_text = ""
        frage = ""
        einheit = ""
        anmerkung = ""
        hilfe_id = 0
        erg = None 
        if typ == 1 or typ == 2:                                     # Addition - 1.Zahl bis 100,0, 2.Zahl bis 10,0           
                zahl1 = random.randint(1,999)/10
                zahl2 = random.randint(1,99)/10
                text = "{} + {}"
                variable = [format_zahl(zahl1,1), format_zahl(zahl2,1)]
                frage = format_zahl(zahl1,1) + "+" + format_zahl(zahl2,1) + "="
                erg = zahl1 + zahl2
                lsg = format_zahl(erg,1)
        if typ == 3:                                                 # Addition - 1.Zahl bis 10,0, 2.Zahl bis 10,00  
                zahl1 = random.randint(1,99)/10
                zahl2 = random.randint(1,999)/100
                text = "{} + {}"
                variable = [format_zahl(zahl1,1), format_zahl(zahl2,2)]
                frage = format_zahl(zahl1,1) + "+" + format_zahl(zahl2,2) + "="
                erg = zahl1 + zahl2
                lsg = format_zahl(erg,2)
        if typ == 4 or typ == 5:                                     # Subtraktion - 1.Zahl bis 100,0, 2.Zahl bis 10,0           
                zahl2 = random.randint(1,99)/10
                zahl1 = random.randint(1,979)/10 + zahl2
                text = "{} - {}"
                variable = [format_zahl(zahl1,1), format_zahl(zahl2,1)]
                frage = format_zahl(zahl1,1) + "-" + format_zahl(zahl2,1) + "="
                erg = zahl1 - zahl2
                lsg = format_zahl(erg,1)
        if typ == 6:                                                 # kleines Einamleins 
                zahl1 = random.randint(2,10)
                zahl2 = random.randint(1,9)/10
                text = "{0} {2} {1}"
                erg = zahl1 * zahl2
                lsg = format_zahl(erg,1)
                hilfe_id = 6
                if random.randint(1,2) == 1:
                    variable = [str(zahl1), format_zahl(zahl2,1), chr(8901)]
                    frage = str(zahl1) + chr(8901) + format_zahl(zahl2,1) + "="
                else:
                    variable = [format_zahl(zahl2,1), str(zahl1), chr(8901)]
                    frage = format_zahl(zahl2,1) + chr(8901) + str(zahl1) + "="
        if typ == 7 or typ == 8:                                     # Multiplikation mit 0,001, 0,01, 0,1, 10, 100, 1000 
                typ2 = random.randint(1,2)
                if typ2 == 1:     
                    zahl1 = random.randint(1,999)/10
                else:
                    zahl1 = random.randint(10,99)/100
                exp = 0
                while exp == 0:
                    exp = random.randint(-3,3)
                if exp >= 0:
                    stellen = 0
                else:
                    stellen = -1*exp
                zahl2 = 10 ** exp
                text = "{0} {2} {1}"
                variable = [format_zahl(zahl1,typ2), format_zahl(zahl2,stellen), chr(8901)]
                frage = format_zahl(zahl1,typ2) + chr(8901) + format_zahl(zahl2,stellen) + "="
                erg = zahl1 * zahl2
                lsg = format_zahl(erg,stellen+typ2)
                hilfe_id = 6        
        if typ == 9:                                                 # Division
                zahl1 = zahl2 = 0
                while zahl1 == zahl2:
                    zahl2 = random.randint(2,9)
                    zahl1 = random.randint(1,9)*zahl2/10
                text = "{2} : {1}"
                erg = zahl1 / zahl2
                lsg = format_zahl(erg,1)
                variable = [format_zahl(zahl1*10,0), str(zahl2), format_zahl(zahl1,1)]
                frage = format_zahl(zahl1,1) + ":" + str(zahl2) + "="
                hilfe_id = 9
        if typ == 10:                                                # Division durch 0,01, 0,01, 0,1, 10, 100, 100
                zahl1 = random.randint(1,99)
                exp = 0
                while exp == 0:
                    exp = random.randint(-2,2)
                if exp >= 0:
                    stellen = 0
                    erg_stellen = exp
                    hilfe_id = 101
                else:
                    stellen = -1*exp
                    erg_stellen = 0
                    hilfe_id = 102
                zahl2 = 10 ** exp
                text = "{1} : {2}"
                variable = [abs(exp), str(zahl1), format_zahl(zahl2,stellen)]
                frage = str(zahl1) + ":" + format_zahl(zahl2,stellen) + "="
                erg = zahl1 / zahl2
                lsg = format_zahl(erg,erg_stellen)
        return typ, typ2, titel, text, pro_text, frage, variable, einheit, anmerkung, [lsg], hilfe_id, erg, {'name':'normal'}

def segment(center_x, center_y, radius, winkel, id = 0, startwinkel = 90):
        rad_start = math.radians(startwinkel)
        rad = math.radians(winkel)        
        start_x = center_x - radius *  math.cos(rad_start)
        start_y = center_y - radius *  math.sin(rad_start) 
        end_x = center_x - radius *  math.cos(rad+rad_start) 
        end_y = center_y - radius *  math.sin(rad+rad_start)
        if winkel <=180:
            largeArcFlag = 0
        else:
            largeArcFlag = 1 
        if id == 2: 
            koordinaten = dict( 
                    start_x2 = start_x, start_y2 = start_y, end_x2 = end_x, end_y2 =  end_y, 
                    largeArcFlag2 = largeArcFlag)
        elif id == 3: 
            koordinaten = dict( 
                    start_x3 = start_x, start_y3 = start_y, end_x3 = end_x, end_y3 =  end_y, 
                    largeArcFlag3 = largeArcFlag)
        else: 
            koordinaten = dict( 
                    start_x = start_x, start_y = start_y, end_x = end_x, end_y =  end_y, 
                    largeArcFlag = largeArcFlag)  
        return koordinaten

def winkel_koordinaten(id, center_x, center_y, radius, winkel, startwinkel, color = "None", symbol = "", schenkel = 0, scheitel = False):
    rad_start = math.radians(startwinkel)
    rad = math.radians(winkel)
    if id == 0:
        koordinaten = dict(center_x = center_x, center_y = center_y, )
    elif id == 1:
        koordinaten = dict(center_x_1 = center_x, center_y_1 = center_y, )
    elif id == 2:
        koordinaten = dict(center_x_2 = center_x, center_y_2 = center_y, )
    elif id == 3:
        koordinaten = dict(center_x_3 = center_x, center_y_3 = center_y, )
    elif id == 4:
        koordinaten = dict(center_x_4 = center_x, center_y_4 = center_y, )
    elif id == 5:
        koordinaten = dict(center_x_5 = center_x, center_y_5 = center_y, )

    # das sind die Schenkel:
    if schenkel > 0:
        x1 = center_x - schenkel *  math.cos(rad_start)
        y1 = center_y - schenkel *  math.sin(rad_start) 
        x2 = center_x - schenkel *  math.cos(rad+rad_start) 
        y2 = center_y - schenkel *  math.sin(rad+rad_start)

        if scheitel == True:
            x3 = center_x + schenkel *  math.cos(rad_start)
            y3 = center_y + schenkel *  math.sin(rad_start) 
            x4 = center_x + schenkel *  math.cos(rad+rad_start) 
            y4 = center_y + schenkel *  math.sin(rad+rad_start)
            if id == 0:
                schenkel_koo = dict(schenkel_1_x = x3, schenkel_1_y = y3, schenkel_2_x = x4, schenkel_2_y = y4) 
            elif id == 1:
                schenkel_koo = dict(schenkel_1_x_1 = x3, schenkel_1_y_1 = y3, schenkel_2_x_1 = x4, schenkel_2_y_1 = y4) 
            elif id == 2:
                schenkel_koo = dict(schenkel_1_x_2 = x3, schenkel_1_y_2 = y3, schenkel_2_x_2 = x4, schenkel_2_y_2 = y4) 
            elif id == 3:
                schenkel_koo = dict(schenkel_1_x_3 = x3, schenkel_1_y_3 = y3, schenkel_2_x_3 = x4, schenkel_2_y_3 = y4)             
            elif id == 4:
                schenkel_koo = dict(schenkel_1_x_4 = x3, schenkel_1_y_4 = y3, schenkel_2_x_4 = x4, schenkel_2_y_4 = y4) 
            elif id == 5:
                schenkel_koo = dict(schenkel_1_x_5 = x3, schenkel_1_y_5 = y3, schenkel_2_x_5 = x4, schenkel_2_y_5 = y4) 
        else:
            if id == 0:
                schenkel_koo = dict(schenkel_1_x = x1, schenkel_1_y = y1, schenkel_2_x = x2, schenkel_2_y = y2)
            elif id == 1:
                schenkel_koo = dict(schenkel_1_x_1 = x1, schenkel_1_y_1 = y1, schenkel_2_x_1 = x2, schenkel_2_y_1 = y2) 
            elif id == 2:
                schenkel_koo = dict(schenkel_1_x_2 = x1, schenkel_1_y_2 = y1, schenkel_2_x_2 = x2, schenkel_2_y_2 = y2) 
            elif id == 3:
                schenkel_koo = dict(schenkel_1_x_3 = x1, schenkel_1_y_3 = y1, schenkel_2_x_3 = x2, schenkel_2_y_3 = y2) 
            elif id == 4:
                schenkel_koo = dict(schenkel_1_x_4 = x1, schenkel_1_y_4 = y1, schenkel_2_x_4 = x2, schenkel_2_y_4 = y2) 
            elif id == 5:
                schenkel_koo = dict(schenkel_1_x_5 = x1, schenkel_1_y_5 = y1, schenkel_2_x_5 = x2, schenkel_2_y_5 = y2)      
        koordinaten.update(schenkel_koo)  
    # das ist der Bogen mit Text:                
    if color:
        start_x = center_x - radius *  math.cos(rad_start)
        start_y = center_y - radius *  math.sin(rad_start) 
        end_x = center_x - radius *  math.cos(rad+rad_start) 
        end_y = center_y - radius *  math.sin(rad+rad_start)
        if winkel <=180:
            largeArcFlag = 0
        else:
            largeArcFlag = 1
        text_x = center_x - radius*3/4 *  math.cos(rad/2+rad_start)
        text_y = center_y - radius/2 *  math.sin(rad/2+rad_start) 
        if id == 0:
            bogen_koo = dict(bogen_radius = radius, sweep_flag = 1, largeArcFlag = largeArcFlag, 
                start_bogen_x = start_x, start_bogen_y = start_y, end_bogen_x = end_x, end_bogen_y =  end_y,
                text_x = text_x, text_y = text_y, color = color, symbol = symbol,)
        if id == 1:
            bogen_koo = dict(bogen_radius_1 = radius, sweep_flag_1 = 1, largeArcFlag_1 = largeArcFlag, 
                start_bogen_x_1 = start_x, start_bogen_y_1 = start_y, end_bogen_x_1 = end_x, end_bogen_y_1 =  end_y,
                text_x_1 = text_x, text_y_1 = text_y, color_1 = color, symbol_1 = symbol,)
        if id == 2:
            bogen_koo = dict(bogen_radius_2 = radius, sweep_flag_2 = 1, largeArcFlag_2 = largeArcFlag, 
                start_bogen_x_2 = start_x, start_bogen_y_2 = start_y, end_bogen_x_2 = end_x, end_bogen_y_2 =  end_y,
                text_x_2 = text_x, text_y_2 = text_y, color_2 = color, symbol_2 = symbol,)
        if id == 3:
            bogen_koo = dict(bogen_radius_3 = radius, sweep_flag_3 = 1, largeArcFlag_3 = largeArcFlag, 
                start_bogen_x_3 = start_x, start_bogen_y_3 = start_y, end_bogen_x_3 = end_x, end_bogen_y_3 =  end_y,
                text_x_3 = text_x, text_y_3 = text_y, color_3 = color, symbol_3 = symbol,)
        if id == 4:
            bogen_koo = dict(bogen_radius_4 = radius, sweep_flag_4 = 1, largeArcFlag_4 = largeArcFlag, 
                start_bogen_x_4 = start_x, start_bogen_y_4 = start_y, end_bogen_x_4 = end_x, end_bogen_y_4 =  end_y,
                text_x_4 = text_x, text_y_4 = text_y, color_4 = color, symbol_4 = symbol,)
        if id == 5:
            bogen_koo = dict(bogen_radius_5 = radius, sweep_flag_5 = 1, largeArcFlag_5 = largeArcFlag, 
                start_bogen_x_5 = start_x, start_bogen_y_5 = start_y, end_bogen_x_5 = end_x, end_bogen_y_5 =  end_y,
                text_x_5 = text_x, text_y_5 = text_y, color_5 = color, symbol_5 = symbol,)
        koordinaten.update(bogen_koo) 
    return koordinaten

def linien_koordinaten(dreh, startwinkel, id = 21):
        schieb_x = math.tan(math.radians(dreh))*50
        if startwinkel in [0,180]:
            dreh = -dreh
            schieb_x = -schieb_x
        if id == 21:                                                    # Stufenwinkel oben rechts
            koordinaten = dict(schieb_bx = 150+schieb_x, schieb_by = 0)
        elif id == 31:                                                  # Stufenwinkel unten rechts
            koordinaten = dict(schieb_bx = -schieb_x, schieb_by = 100)
        elif id == 41:                                                  # Stufenwinkel unten links
            koordinaten = dict(schieb_bx = -schieb_x, schieb_by = 100)
        koordinaten1 = dict(dreh = dreh, schieb_ox = schieb_x)
        koordinaten.update(koordinaten1)  
        return koordinaten

def viereck(a,y_schieb,alfa,beta,delta=0 ):
    h = 100
    delta_1 = delta -90
    r = a * math.tan(math.radians(delta_1))
    p = h/math.tan(math.radians(alfa))    
    q = (h+r)/math.tan(math.radians(beta))
    ax = (400 - a - p - q)/2    
    dx = ax + p
    bx = ax + a + p + q
    cx = ax + a + p
    ay = by = h + r +y_schieb
    dy = y_schieb + r
    cy = y_schieb    
    koordinaten = dict(ax=ax, ay=ay, bx=bx, by=by, cx=cx, cy=cy, dx=dx, dy=dy)
    return koordinaten

def winkel(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "":                                                               
        typ_anf = 2
        typ_end = 5
        if "Parallele" in optionen or jg >= 7 or stufe > 7:
            typ_end = 7
        return typ_anf, typ_end
    elif eingabe != "":
        if typ in [1,2]:
            wert = int(lsg[0]) 
            if abs(eingabe - wert) <=5:
                return 1, "<br>Genauer wäre {}°.".format(wert)
            elif abs(eingabe - wert) <= 10:
                return 0.5, "<br>Genauer wäre {}° - dafür gibt es nur einen halben Punkt.".format(wert)
            return -1, "" 
        elif  typ == 3 or (typ == 4 and typ2 == 2):
            if eingabe.upper() == lsg[0].upper() or eingabe.upper() == lsg[1].upper():
                return 0, "Achte auf Groß- und Kleinschreibung!" 
            return -1, ""
        return -1, ""
    else: 
        typ = random.randint(typ_anf, typ_end)
        typ2 = 0
        titel = "Winkel" 
        text = ""
        variable = ["",]
        pro_text = frage = einheit = anmerkung = ""
        hilfe_id = 0
        erg = None 
        y_schieb = 20  
        symbol_liste = ["α", "β", "γ", "δ"]
        symbol = random.choice(symbol_liste)
        variable = [symbol]
        parameter = {'name': 'svg/winkel.svg', 'object': 'winkel'}
        center_x = 200 
        center_y = 100
        bogen_radius = 40 
        color = 'lightskyblue'
        if typ in [1,2]:                                                # Winkel schätzen
            typ2 = random.randint(1,2)
            if typ2 ==1:
                winkel = random.randint(1,9)*10
            else:
                winkel = random.randint(1,27)*10
            startwinkel = 180-winkel/2
            text = "Schätze die Größe des Winkels {}?"
            pro_text = "Winkel schätzen"
            frage = "{}≙"
            einheit = "°"
            erg = winkel
            if winkel in [90,180,270]:
                text = "Wie groß ist der Winkel {}?"
                anmerkung = "Diesen Winkel solltest du kennen und genau angeben."
                lsg = [str(erg)]   
            else:
                anmerkung = "Du sollst schätzen und nicht messen!<br>Gewertet wird eine Abweichung von ± 5°."
                lsg = [str(erg),"indiv_0"] 
            hilfe_id = 11
        elif typ == 3:                                                  # Winkelarten
            typ2 = random.random()
            if typ2 < 0.9:
                winkel = random.randint(0,36)*10
                startwinkel = 180-winkel/2
                symbol = str(winkel)+"°"
                if winkel == 360:
                    winkel = 359.99
                    startwinkel = 0
                    symbol = 360
                text = "Um welche Winkelart handelt es sich hier?"
                pro_text = "Winkelart"
                frage = "Das ist ein" 
                einheit = "Winkel"
                if winkel == 0:
                    lsg = ["Nullwinkel","Null"]
                elif winkel == 90:
                    lsg = ["rechter Winkel", "rechter"] 
                elif winkel == 180:
                    lsg = ["gestreckter Winkel", "gestreckter"]
                elif winkel > 359:
                    lsg = ["Vollwinkel","Voll"]
                elif winkel < 90:
                    lsg = ["spitzer Winkel","spitzer"]
                elif winkel < 180:
                    lsg = ["stumpfer Winkel","stumpfer"]
                else:
                    lsg = ["überstumpfer Winkel","überstumpfer", "überstumpf"]
                hilfe_id = 31
            else:
                winkel = random.randint(11,111)
                startwinkel = 180-winkel/2
                pro_text = "Benennungen"
                einheit = "" 
                if typ2 > 0.95:
                    text = "Wie nennt man diese beiden Halbgeraden, die einen Winkel begrenzen?"
                    frage = "Das sind die"
                    lsg = ["Schenkel", "Winkelschenkel"]
                else:
                    text = "Wie nennt man diesen Punkt an dem sich die beiden Winkelschenkel treffen?"
                    frage = "Das ist der"
                    lsg = ["Scheitelpunkt", "Scheitel"]
            lsg.append("indiv_0")
            typ2 = 0              
        elif typ == 4:                                                  # Scheitelwinkel und Nebenwinkel
            typ2 = random.random()
            winkel = random.randint(10,111)
            color2 = "yellow"
            if typ2 < 0.5:
                pro_text = "Scheitelwinkel"
                winkel2 = symbol2 = winkel
                startwinkel = 180-winkel/2
                startwinkel2 = -winkel/2
                if typ2 < 0.4:
                    symbol2 = str(symbol2) + "°"
                    erg = winkel
                    lsg = [str(erg)]  
                    if stufe%2==1:
                        hilfe_id = 41
                    else:
                        hilfe_id = 42
                else:
                    typ2 = 2
                    lsg = ["Scheitelwinkel", "Scheitel", "indiv_0"]
                    hilfe_id = 1
            else:
                pro_text = "Nebenwinkel"
                winkel2 =  180-winkel 
                winkel2 = symbol2 = 180-winkel 
                startwinkel = 180-winkel
                startwinkel2 = 0
                if typ2 < 0.9:
                    symbol2 = str(symbol2) + "°"
                    erg = winkel
                    lsg = [str(erg)]
                    if stufe%2==1:
                        hilfe_id = 43
                    else:
                        hilfe_id = 44
                else:
                    typ2 = 2
                    lsg = ["Nebenwinkel", "Neben", "indiv_0"]
                    hilfe_id = 1
            if typ2 == 2:
                text = " Diese beiden Winkel sind gleich groß - wie heißt so ein Winkelpaar?"
                symbol2 = "α"
                symbol = "β"
                frage = "Das sind"
                einheit = "winkel"  
            else:
                text = "Wie groß ist der Winkel {}?"
                frage = "{}≙"
                einheit = "°"
            koordinaten = winkel_koordinaten(1, center_x, center_y, bogen_radius, winkel2, startwinkel2, color2, symbol2, 100, False)
            parameter.update(koordinaten)
        elif typ == 5:                                                  # Winkel an Dreieck und Viereck
            if stufe%2 == 1:
                typ2 = random.randint(1,4)
            else:
                typ2 = random.randint(1,3)
            if typ2 == 1:                                               # Winkel am Viereck
                titel = pro_text = "Winkel am Viereck"
                text = "Wie groß ist der Winkel {}?"
                alfa = 90-random.randint(0,6)*5
                beta = 90-random.randint(-2,6)*5
                delta = 90+random.randint(0,4)*5
                delta_anz = delta + (90-alfa)
                gamma = 360-alfa-beta-delta_anz
                a=random.randint(100,140)+abs(90-alfa)+abs(90-beta)
                ecken = 4
                hilfe_id = 61
            elif typ2 == 2:                                             # Winkel am Dreieck
                titel = pro_text = "Winkel am Dreieck"
                text = "Wie groß ist der Winkel {}?"
                alfa = 90-random.randint(5,12)*5
                beta = 90-random.randint(5,12)*5
                delta = delta_anz = 0
                gamma = 180-alfa-beta
                a=0  
                ecken = 3             
                hilfe_id = 62
            elif typ2 in (3,4):                                         # regelmäßige Vielecke  
                ecken_liste = ['3', '4','6','12', '5', '10']
                if typ2 == 4:                                               # auch Winkel außen
                    ecken = int(random.choice(ecken_liste[:4]))
                    hilfe_id = 64
                    hilfe_text = "Zunächst musst du die Größe des blauenWinkels bestimmen (der gelbe Kreis hat 360°).<br>Die Winkelsumme im Dreieckbeträgt 180°."
                else:
                    ecken = int(random.choice(ecken_liste))
                    hilfe_id = 63
                    hilfe_text = "Der gelbe Kreis hat einen Winkel von 360°, den musst du nur entsprechend aufteilen."
                alfa = int(360/ecken)
                beta = int(180-alfa)/2
                bogen_radius = 30 
                rotate = list(range(alfa,ecken*alfa,alfa))
                startwinkel = 180-alfa/2
                text = "Wie groß ist der rote Winkel in diesem {}-Eck?".format(ecken)
                pro_text = "Winkel am {}-Eck".format(ecken)
                frage = "Er hat"
                einheit = "°"
                erg = alfa
                parameter.update({'object': 'n-eck', 'n_eck': ecken, 'rotate': rotate,}) 
                koordinaten_dreieck = winkel_koordinaten(0, center_x, center_y, bogen_radius, alfa, startwinkel, "red", "", 100)  
                parameter.update(koordinaten_dreieck)
                if typ2 == 4:                                               # Winkel außen
                    koordinaten_aussen = winkel_koordinaten(2, koordinaten_dreieck['schenkel_1_x'], koordinaten_dreieck['schenkel_1_y'], bogen_radius, beta, 270, "red", "", 100)  
                    parameter.update(koordinaten_aussen)
                    parameter.update({'color1': "red", 'color': color})
                    erg = beta    
        elif typ == 6:                                                  # Stufen- und Wechselwinkel
            winkel = random.randint(60,120)
            if random.random() < 0.5:                       # Winkel rechts
                startwinkel = 180-winkel
            else: 
                startwinkel = 0
            #startwinkel = 180-winkel
            parameter["object"] = "stufen"
            anmerkung = "Die Geraden sind jeweils parallel."
            erg = None
            center_x = 120
            center_y = 50
            id2 = random.randint(2,4)*10+1
            typ2 = random.random()
            if typ2 < 0.5:
                pro_text = "Stufenwinkel"
                startwinkel2 = startwinkel
                if typ2 > 0.4:
                    typ2 = 2
                    lsg = ["Stufenwinkel", "Stufen", "indiv_0"]
                    hilfe_id = 1
                else:
                    if stufe%2==1:
                        hilfe_id = 51
                    else:
                        hilfe_id = 52
            else:
                pro_text = "Wechselwinkel"
                if startwinkel != 0:
                    startwinkel2 = 360-winkel
                else:
                    startwinkel2 = 180
                #startwinkel2 = 30
                if typ2 > 0.9:
                    typ2 = 2
                    lsg = ["Wechselwinkel", "Wechsel", "indiv_0"]
                    hilfe_id = 1
                else:
                    if stufe%2==1:
                        hilfe_id = 53
                    else:
                        hilfe_id = 54
            if typ2 != 2:
                text = "Wie groß ist der Winkel {}?"
                frage = "{}≙"
                einheit = "°" 
                symbol2 = symbol
                symbol = str(winkel)+"°"
                color2 = 'yellow'
                erg = winkel
                lsg = [str(erg)]  
            else:
                frage = "Das sind"
                einheit = "winkel"
                symbol = "α"
                symbol2 = "β"
                color2 = color
                text = " Diese beiden Winkel sind gleich groß - wie heißt so ein Winkelpaar?"
            koordinaten = winkel_koordinaten(1, center_x, center_y, bogen_radius, winkel, startwinkel, color, symbol, 100)
            parameter.update(koordinaten) 
            koo_winkel = winkel_koordinaten(2, center_x, center_y, bogen_radius, winkel, startwinkel2, color2, symbol2)  
            parameter.update(koo_winkel) 
            koo_ecken = linien_koordinaten(90-winkel, startwinkel, id2)                                                                                      # die Drehung der Parallelen'
            parameter.update(koo_ecken)
        elif typ == 7:                                                  # Thaleskreis
            titel = pro_text = "Winkel"
            text = "Wie groß ist der Winkel {}?"
            alfa = 90-random.randint(5,12)*5
            beta = 90-alfa
            delta = delta_anz = 0
            gamma = 180-alfa-beta
            a=0
            ecken = 2
            y_schieb = 50  
            hilfe_id = 71 
        if typ <= 4:
            koordinaten = winkel_koordinaten(0, center_x, center_y, bogen_radius, winkel, startwinkel, color, symbol, 100)
            parameter.update(koordinaten) 
        elif typ != 6: 
            if typ2 in (1,2) or typ == 7 :                               # Winkel alfa und beta  
                parameter.update({'object': 'viereck'})
                koordinaten = viereck(a,y_schieb,alfa,beta,delta)
                parameter.update(koordinaten)
                color = ["lightskyblue","lightskyblue","lightskyblue","lightskyblue",]
                erg_liste = [alfa, beta, gamma,delta_anz]
                winkel_text = [str(alfa)+"°", str(beta)+"°", str(gamma)+"°", str(delta_anz)+"°"]
                zuza = random.randint(0,ecken-1)
                color[zuza] = "yellow"
                winkel_text[zuza] = symbol_liste[zuza]
                erg = erg_liste[zuza]
                lsg = [str(erg)]  
                variable = [symbol_liste[zuza]]
                frage =variable[0]+"="
                einheit = "°"

                # Winkel Alfa:
                center_x = (koordinaten ["ax"])
                center_y = (koordinaten ["ay"]) 
                koordinaten_alfa = winkel_koordinaten(2, center_x, center_y, bogen_radius, alfa, 180-alfa, color[0], winkel_text[0], 100)  
                parameter.update(koordinaten_alfa)

                # Winkel Beta:
                center_x = (koordinaten ["bx"])
                center_y = (koordinaten ["by"])
                koordinaten_beta = winkel_koordinaten(1, center_x, center_y, bogen_radius, beta, 0, color[1], winkel_text[1], 100)  
                parameter.update(koordinaten_beta)

            if typ2 in (1,2):                                            # Winkel Gamma und delta
                # Winkel Gamma:
                center_x = (koordinaten ["cx"])
                center_y = (koordinaten ["cy"]) 
                koordinaten_gamma = winkel_koordinaten(3, center_x, center_y, bogen_radius, gamma,  270-(90-beta), color[2], winkel_text[2], 100)  
                parameter.update(koordinaten_gamma)

                # Winkel Delta:
                center_x = (koordinaten ["dx"])
                center_y = (koordinaten ["dy"]) 
                koordinaten_delta = winkel_koordinaten(4, center_x, center_y, bogen_radius, delta+(90-alfa), 180+(90-delta), color[3], winkel_text[3], 100)  
                parameter.update(koordinaten_delta) 

            if typ == 7:                                                 # Thaleskreis
                thales = ((koordinaten ["bx"])-(koordinaten ["ax"]))/2
                parameter.update({'object': 'thales', 'thales': thales}) 
        return typ, typ2, titel, text, pro_text, frage, variable, einheit, anmerkung, lsg, hilfe_id, erg, parameter

def bruchteile(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "":                                                               
        typ_anf = 1
        typ_end = 5
        if stufe%1 != 0:                                        # nur für Gymnasium in A-Kurs'
            typ_end = 6
        return typ_anf, typ_end
    elif eingabe != "":                                                                                                         
        if typ == 1:
            parser = Parser()
            if (parser.evaluate(lsg[0],{})) == (parser.evaluate(eingabe,{})):
                return 0, "Das ist fast richtig, du sollst hier aber nicht kürzen"
            return -1, ""
        else:
            return -1, ""
    else:                                                                            
        typ = random.randint(typ_anf, typ_end)
        titel = "Bruchteile" 
        text = "default{}"
        variable = ["",]
        pro_text = ""
        frage = ""
        einheit = ""
        anmerkung = ""
        hilfe_id = 0
        erg = None 
        if typ == 1:
            center_x = 160 
            center_y = 80
            radius = 80 
            nenner = random.randint(2,12)
            zaehler = random.randint(1,nenner-1)
            winkel = [[0,"LightSkyBlue"]]
            item = [0,""]
            n = 1
            while n < nenner:
                if n < zaehler:
                  item = (int(n*360/nenner),"LightSkyBlue")
                else:
                  item = (int(n*360/nenner),None)
                winkel.append(item)
                n +=1
            text = "Welcher Bruch ist hier dargestellt?"
            anmerkung="(Den Bruch musst du mit dem ""/""-Zeichen eingeben)"
            lsg = [str(zaehler)+"/"+str(nenner),"indiv_0"]
            parameter = {'name': 'svg/winkel.svg', 'object': 'bruchteile', 'nenner': nenner, 'winkel': winkel}
            koordinaten = dict(center_x = center_x, center_y = center_y, radius = radius, sweep_flag = 1)
            koordinaten1 = segment(center_x, center_y, radius, 360/nenner)
            koordinaten.update(koordinaten1)
            parameter.update(koordinaten)
        elif typ == 2:
            nenner=7
            spalte=zeile=zaehler=5
            while zeile*spalte%nenner>0 or zaehler>=nenner:
                nenner = random.randint(2,10)
                zaehler = random.randint(1,nenner)
                zeile = random.randint(3,7)
                spalte = random.randint(3,7)
            bruch = Fraction(zaehler/nenner).limit_denominator()
            zaehler = bruch.numerator
            nenner = bruch.denominator
            koordinaten = []
            for y in range(zeile):
                for x in range(spalte):
                    koordinaten.append((x * 15, y * 15, 0))
            text = "Wie viele der {} Kästchen müsstest du färben, wenn {}/{} der Kästchen in diesem Rechteck gefärbt werden sollen?"
            pro_text = "{1}/{2} von {0} Kästchen"
            variable = [spalte*zeile,zaehler, nenner]
            erg = spalte*zeile*zaehler/nenner
            lsg = [str(erg)]
            einheit = "müssten gefärbt werden"
            parameter = {'name': 'svg/winkel.svg', 'object': 'kaestchen', 'schieb': koordinaten,}
        else:
            zahl1=zaehler=nenner=1
            while zahl1%nenner>0 or zaehler>=nenner :
                nenner = random.randint(2,10)
                zaehler = random.randint(1,nenner)
                zahl1 = random.randint(2*nenner,3*nenner)
            einh = ["Euro", "€", "m", "kg",""]
            einheit = random.choice(einh)
            if typ == 3:
                titel = "Ergänze zum Ganzen"
                text = "Ergänze zum Ganzen: {}/{} von x = {}{}"
                frage = "x="
                variable = [zaehler, nenner, int(zahl1*zaehler/nenner), einheit]
                erg = zahl1
                lsg = str(erg)
                if stufe%2 == 1:
                    if zaehler == 1:
                        hilfe_id = 31
                    else:                        
                        hilfe_id = 32
                else:
                    if zaehler == 1:
                        hilfe_id = 33
                    else:
                        hilfe_id = 34
            elif typ == 4 or typ == 5:
                text = "Berechne {}/{} von {}{}"
                frage = "{}/{}·{}"
                variable = [zaehler, nenner, zahl1,einheit]
                erg = zahl1*zaehler/nenner
                lsg = str(erg)  
                if stufe%2 == 1:
                    if zaehler == 1:
                        hilfe_id = 41
                    else:
                        hilfe_id = 42
                else:
                    if zaehler == 1:
                        hilfe_id = 43
                    else:
                        hilfe_id = 44
            else:                                                   # Bruchteile größer einem Ganzen
                ganze = random.randint(1,2)    
                text = "Berechne {} {}/{} von {}{}"
                frage = "{} {}/{}·{}"
                zaehler=nenner=5
                while zaehler>=nenner:
                    nenner = random.choice([2,3,4,5,10])
                    zaehler = random.randint(1,nenner)
                zahl1=nenner*random.randint(1,5)
                bruch = Fraction(zaehler/nenner).limit_denominator()
                zaehler = bruch.numerator
                nenner = bruch.denominator
                variable = [ganze, zaehler, nenner, zahl1,einheit]
                erg = ganze*zahl1+zahl1*zaehler/nenner
                lsg = str(erg)
                if stufe%2 == 1:
                    if zaehler == 1:
                        hilfe_id = 51
                    else:
                        hilfe_id = 52
                else:
                    if zaehler == 1:
                        hilfe_id = 53
                    else:
                        hilfe_id = 54
            parameter = {'name': 'normal'}
        return typ, 0, titel, text, pro_text, frage, variable, einheit, anmerkung, lsg, hilfe_id, erg, parameter

def gemischte_zahl(zaehler, nenner):
    if zaehler%nenner == 0:                                                             # ganze Zahl
        term_a = term_b =str(zaehler // nenner) 
    elif zaehler//nenner != 0:                                                          # gemischte Zahl
        term_a = str(zaehler // nenner) + " " + str(Fraction(zaehler%nenner,nenner))
        term_b = str(zaehler // nenner) + "+" + str(Fraction(zaehler%nenner,nenner))
    else:                                                                               # echter Bruch
        term_a = term_b  = str(Fraction(zaehler,nenner))
    return term_a, term_b

def kuerzen(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "":                                                               
        typ_anf = 1
        typ_end = 7
        return typ_anf, typ_end
    elif eingabe != "":
        if typ >= 4:                                                                                       # kürzen
            parser = Parser()
            try:
                if "/" not in lsg[1]:
                    if int(eingabe == int(lsg[1])):
                        return 1, ""
                    else:
                        return 0, "Das richtige Ergebnis ist eine ganze Zahl!"
                else:
                    wert = parser.evaluate(lsg[1],{})
                    if wert > 1:
                        eingabe = eingabe.strip().replace("  "," ").replace(" ","+")
                    if round(wert,6) == round(parser.evaluate(eingabe,{}),6): 
                        if wert > 0 and lsg[1].split("/")[-1] == eingabe.split("/")[-1]:   
                            return 0, "das ist ein unechter Bruch - den sollst du in eine gemischte Zahl umwandeln!"
                        else:
                            return 0, "hier kann man noch weiter kürzen"
            except:
                return 0, "Da stimmt was nicht - den Term kann ich nicht berechnen"
        elif typ > 1:
            if int(lsg[0])%eingabe == 0:
                return 0, "Das ist zwar ein gemeinsamer Teiler aber nicht der größte!"
        return -1, ""
    else:                                                                            
        titel = "Kürzen"
        typ = random.randint(typ_anf, typ_end) 
        einheit = ""
        anmerkung = ""
        hilfe_id = 0
        erg = None 
        if typ > 2:
            zahl2 = 8
            zahl3 = 2
        else:
            if stufe%2 == 0:
                zahl2=17
                zahl3=2
            else:
                zahl2=13
                zahl3=random.randint(2,3)						                                #größere Nenner für E-Kurs	
        if zahl3==3 :						
            zaehler=random.randint(2,zahl2)*random.randint(1,2)	                                #größere Zähler bei größeren Nennern
        else:
            zaehler=random.randint(2,zahl2)	
        nenner=zaehler
        if typ == 1:
            while lcm(zaehler,nenner) > 4*max(zaehler,nenner) or ggt(nenner,zaehler) == 1 or zaehler==nenner :
                nenner=random.randint(2,zahl2)*zahl3
        else:
            while ggt(nenner,zaehler) == 1 or zaehler==nenner:
                nenner=random.randint(2,zahl2)*zahl3
        if zaehler==11 :
            zahl3==random.randint(3,11)
            nenner=11*random.randint(3,11)
            while zaehler>=nenner:
                zaehler=11*random.randint(1,10)					                                #ergibt z.B. 77/88
        variable = [zaehler, nenner] 
        if typ == 1:                                                                # kgV
            titel="kgV"	
            text = "Was ist der das kleinste gemeinsame Vielfache von {} und {}?"
            pro_text = frage = "kgV({},{})" 
            erg = lcm(zaehler, nenner)
            lsg = [str(erg)]
            hilfe_id = 11
        elif typ <= 3:                                                              # ggT
            titel="ggT"
            text = "Was ist der größte gemeinsame Teiler von {} und {}?"
            pro_text = frage = "ggT({},{})" 
            erg = ggt(zaehler, nenner)
            lsg = [str(erg), "indiv_0"]
        elif typ <= 5:                                                              # kürzen
            faktor = [1,2,3,5,10,11]
            teiler_liste = [3,8,9,25]
            exp = random.randint(0,1)
            teiler = random.choice(teiler_liste) 
            zaehler = nenner = 1
            while zaehler >= nenner:
                nenner = random.choice(faktor)*teiler*10**exp
                zaehler = random.choice(faktor)*teiler*10**exp
            bruch = Fraction(zaehler/nenner).limit_denominator()                    # gekürzter Bruch!
            text = "Kürze den Bruch {}/{} so weit wie möglich!"
            pro_text = frage = "{}/{}≈"
            anmerkung = "Hier solltest du die Teilbarkeitsregeln anwenden"
            if teiler == 3 or teiler == 9:
                hilfe_id = 41
            variable = [zaehler, nenner]
            pro_text = frage = "{}/{}≈"
            lsg = [str(bruch),str(bruch),"indiv_0"]
        else:                                                                       # das habe ich größtenteils aus dem Rechentrainer.1 übernommen:
            text = "Kürze den Bruch {}/{} so weit wie möglich und wandele unechte Brueche in gemischte Zahlen um!"
            pro_text = frage = "{}/{}≈"
            erg = None
            term_a, term_b = gemischte_zahl(zaehler, nenner)
            if zaehler%nenner == 0:                                                             # ganze Zahl
                hilfe_id = 31
            elif zaehler//nenner != 0:                                                          # gemischte Zahl
                if stufe%2== 1:
                    hilfe_id = 32
                else:
                    hilfe_id = 33
            else:                                                                               # echter Bruch
                if stufe%2== 1:
                    hilfe_id = 34
                else:
                    hilfe_id = 35
            lsg = [term_a, term_b,"indiv_0"]
        return typ, 0, titel, text, pro_text, frage, variable, einheit, anmerkung, lsg, hilfe_id, erg, {'name':'normal'}

def bruch_komma(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "":                                                               
        typ_anf = 1
        typ_end = 9
        if stufe >= 6 or jg >= 7 or "mit" in optionen:
            typ_end = -typ_end
        return typ_anf, typ_end
    elif eingabe != "":
        if typ   == 2:                                                                          # Kommazahl mal Bruch                                                             
            if "/" not in lsg[1]:
                if int(eingabe == int(lsg[1])):
                    return 1, ""
                else:
                    return 0, "Das richtige Ergebnis ist eine ganze Zahl!"
            else:
                if "/" not in eingabe:
                    return 0, "Du musst einen Bruch mit dem '/' Zeichen eingeben" 
                else:
                    parser = Parser()
                    try:                 
                        wert = parser.evaluate(lsg[1],{})
                        if wert > 1:
                            eingabe = eingabe.strip().replace("  "," ").replace(" ","+")
                            if wert > 0 and lsg[1].split("/")[-1] == eingabe.split("/")[-1]:   
                                return 0, "das ist ein unechter Bruch - den sollst du in eine gemischte Zahl umwandeln!"
                        if round(wert,6) == round(parser.evaluate(eingabe,{}),6):
                            return 0, "hier kann man noch weiter kürzen"
                    except:
                        return 0, "Da stimmt was nicht - den Term kann ich nicht berechnen"
        elif typ >= 4 and typ <= 6:                                                             # Bruch in Komma
            from decimal import Decimal
            if round(eingabe,4) == round(Decimal(lsg[0]),4):
                return 1, ""
            elif round(eingabe,3) == round(Decimal(lsg[0]),3):
                return 0, "Du sollst auf 4 Stellen runden!"
        elif typ >= 7:                                                                          # Komma in Bruch
            parser = Parser()
            try:
                if "/" not in eingabe:
                    return 0, "Du musst ein Bruch mit dem '/' Zeichen eingeben"
                else:
                    wert = parser.evaluate(lsg[0],{})
                    if round(wert,6) == round(parser.evaluate(eingabe,{}),6): 
                        return 0, "hier kann man noch weiter kürzen"
            except:
                return 0, "Da stimmt was nicht - den Term kann ich nicht berechnen"
        return -1, ""
    else: 
        if typ_end < 0:                                                                         # auch periodische Dezimalzahlen
            typ2 = 1
            typ_end = abs(typ_end)
        else:
            typ2 = 0                                                                           
        typ = random.randint(typ_anf, typ_end) 
        titel = "Bruch und Kommazahl" 
        einheit = anmerkung = ""
        hilfe_id = 0
        erg = None 
        nenner_liste = [100,2,4,5,8,10,3]
        if (typ == 4 and typ2 == 0) or typ == 3:                                                # keine periodischen Dezimalzahlen
            nenner_liste = nenner_liste[:-1]
        if typ <= 3 :                                                                           # kein nenner 100
            nenner_liste = nenner_liste[1:]
        #if typ >= 3:                                                                           # Bruch <-> Kommazahl
        nenner = random.choice(nenner_liste)
        if nenner == 8:
            zaehler = random.randint(1,2)
            if stufe%2 == 1:
                zaehler = 3
        else:
            zaehler = nenner
            while ggt(zaehler,nenner) != 1:
                zaehler = random.randint(1,nenner-1)
        if typ   == 1:                                                                          # Kommazahl mal Bruch
            kommazahl = 10
            while kommazahl%10==0:
                kommazahl = random.randint(1,15)*4
            text = "Multipliziere {} · 1/{}"
            pro_text = frage = "{}·1/{}" 
            variable = [str(kommazahl/10).replace(".",","), nenner]
            erg = kommazahl/10/nenner
            lsg = [str(erg)]
            hilfe_id = 11
            if nenner == 5:
                hilfe_id = 12
        elif typ == 2:                                                                          # Bruch mal ganze Zahl                                                                     
            text = "Multipliziere {} · {}/{} und gib das Ergebnis als gekürzten Bruch an"
            pro_text = frage = "{}·{}/{}" 
            zahl1 = random.randint(2,5)
            variable = [zahl1,zaehler,nenner]
            zaehler = zaehler * zahl1
            bruch = Fraction(zaehler,nenner)
            term_a, term_b = gemischte_zahl(zaehler, nenner)
            hilfe_id = 21
            lsg = [term_a, term_b,  "indiv_0"] #"indiv_1"]            
        elif typ == 3:                                                                          # Kommazahl + Bruch
            kommazahl = 10
            while kommazahl%10==0:
                kommazahl = random.randint(1,15)*4
            kommazahl /=10
            text = "Addiere {} + {}/{}"
            pro_text = frage = "{}+{}/{}=" 
            variable = [str(kommazahl).replace(".",","),zaehler,nenner]
            wert  = kommazahl+zaehler/nenner
            bruch = Fraction(wert).limit_denominator(1000)
            term_a, term_b = gemischte_zahl(bruch.numerator, bruch.denominator)
            hilfe_id = 31
            erg = wert
            lsg = [str(wert)] 
        elif typ <= 6:                                                                          # Bruch in Kommazahl
            text = "Wandle den Bruch {}/{} in eine Dezimalzahl um!"
            pro_text = frage = "{}/{}≙"
            if nenner == 3:
                anmerkung = "(Runde bei periodischen Zahlen auf 4 Stellen nach dem Komma)"
            variable = [zaehler, nenner]
            erg = zaehler/nenner
            lsg = [str(erg),"indiv_0"]
            if zaehler == 1:
                hilfe_id = 41
            else:
                hilfe_id = 42
        else:                                                                                   # Kommazahl in Bruch
            text = "Wandle die Dezimalzahl {} in einen gekürzten Bruch um!"
            pro_text = frage = "{}≙"
            if Zaehler == 1:
                hilfe_id = 41
            else:
                hilfe_id =62
            if nenner == 3:
                if zaehler ==1:
                    kommazahl = "0,333..."
                else:
                    kommazahl = "0,666..."
            else:
                kommazahl = str(zaehler/nenner).replace(".",",")
            variable = [kommazahl]
            bruch = Fraction(zaehler/nenner).limit_denominator()                    #gekürzter Bruch!
            lsg = [str(bruch),"indiv_0"]
        return typ, 0, titel, text, pro_text, frage, variable, einheit, anmerkung, lsg, hilfe_id, erg, {'name':'normal'}

def zaehler_faerben(nenner, zaehler, farbe):
    winkel = []
    for n in range(nenner):
        winkel.append((
            int(n * 360 // nenner),
            farbe if n < zaehler else None
        ))
    return winkel
  
def brueche_erzeugen(kgv_max):
    nenner_1 = nenner_2 = 1
    while lcm(nenner_1, nenner_2) >= kgv_max or nenner_1 == nenner_2:
        nenner_1 = random.randint(2,10)
        nenner_2 = random.randint(2,10)
    zaehler_1 = random.randint(1, nenner_1-1)
    zaehler_2 = random.randint(1, nenner_2-1)
    bruch_1 = Fraction(zaehler_1/nenner_1).limit_denominator()
    bruch_2 = Fraction(zaehler_2/nenner_2).limit_denominator()
    return bruch_1, bruch_2

def bruchrechnung(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "":                                                               
        typ_anf = 3
        typ_end = 4
        if "ion" in optionen:
            typ_end = 6
        if jg > 8:
            typ_anf = 1
        elif stufe > 1 or "gleichnamig" in optionen:
            if stufe%2 > 1:
                typ_anf = 1
            else:
                typ_anf = 2
        return typ_anf, typ_end
    elif eingabe != "":
            try:
                parser = Parser()
                wert = parser.evaluate(lsg[2],{})
                if wert > 1:
                    eingabe = eingabe.strip().replace("  "," ").replace(" ","+")
                if round(wert,6) != round(parser.evaluate(eingabe,{}),6):
                    return -1, ""
                else:
                    eingabe = eingabe.replace(" ","")                                                                                    # kürzen
                    if "/" not in lsg[0]:
                        if eingabe == lsg[0]:
                            if typ2 <=6:
                                return 1.5, "<br>Für die Umwandlung in eine ganze Zahl gibt es einen halben Extrapunkt!"
                            else:
                                return 1, ""
                        else:
                            return 1, "<br>Aber besser wäre die Antwort: " + eingabe + "=" + lsg[0]
                    else:
                        if wert > 1:
                            if eingabe ==lsg[2] in eingabe:
                                if typ2 <= 6: 
                                    return 1.5, "<br>Für die Umwandlung in eine gemischte Zahl gibt es einen halben Extrapunkt!"
                                else:
                                    return 1, ""                            
                            else:
                                return 1, "<br>Das ist ein unechter Bruch - den hättest du in eine gemischte Zahl umwandeln können: " + eingabe + "="  + lsg[0]
                        elif eingabe == lsg[0] and lsg[0] != lsg[1]:
                                return 1.5, "<br>Fürs Kürzen gibt es einen halben Extrapunkt!"
                        else:
                            if lsg[0] == eingabe: 
                                return 1, ""
                            else:                        
                                return 1, "<br>Aber du hättest du noch weiter kürzen können: " + eingabe + "=" + lsg[0]
            except:
                return 0, "Da stimmt was nicht - du musst das Ergebnis entweder als Bruch (z.B. 1/2) oder als gemischte Zahl (z.B. 1 1/2) eingeben oder u.U. als ganze Zahl."
    else:                                                                            
        typ = random.randint(typ_anf, typ_end) 
        #typ=2
        if stufe%2 == 1:
            typ2 = 1
        else:
            typ2 = 0        
        titel = "Bruchrechnung" 
        text="Berechne, kürze und wandle in eine gemischte Zahl um (falls möglich):<br><br>{}{} {} {} ="
        anmerkung="(Für das Kürzen und auch für die Umwandlung in gemischte Zahlen gibt es u.U. Extrapunkte.)"   
        pro_text = frage = einheit = anmerkung = hilfe = ""
        ganz = ""
        hilfe_id = 0
        erg = None 
        parser = Parser()
        if typ <= 2:
            anmerkung="Wenn du nicht weißt, wie man das rechnet, solltest du mal auf 'Hilfe' klicken!<br>" + anmerkung
            #typ2=7
            ganz = ""
            if stufe%2 == 1:
                kgv_max = 30
            else:
                kgv_max = 20
            bruch_1 = bruch_2 = 2
            if typ == 2:                                                                        # Addition
                while bruch_1 + bruch_2 > 1:
                    bruch_1, bruch_2 = brueche_erzeugen(kgv_max)
                zeichen = "+"
                farbe2 = "LightSkyBlue"
            else:                                                                               # Subtraktion
                while bruch_2 >= bruch_1:
                    bruch_1, bruch_2 = brueche_erzeugen(kgv_max)
                zeichen = "-"               
                farbe2 = "orangered"
            nenner_1 = bruch_1.denominator                                                      # hier werden die beiden Brüche gekürzt
            nenner_2 = bruch_2.denominator
            zaehler_1 = bruch_1.numerator 
            zaehler_2 = bruch_2.numerator
            kgv = lcm(nenner_1, nenner_2)
            if typ == 2:
                bruch_lsg = Fraction(((zaehler_1*nenner_2)+(zaehler_2*nenner_1))/(nenner_1*nenner_2)).limit_denominator()
                ungekuerzt = str(zaehler_1*int(kgv/(nenner_1))+zaehler_2*int(kgv/(nenner_2)))+"/"+str(kgv)
            else:
                bruch_lsg = Fraction(((zaehler_1*nenner_2)-(zaehler_2*nenner_1))/(nenner_1*nenner_2)).limit_denominator()
                ungekuerzt = str(zaehler_1*int(kgv/nenner_1)-zaehler_2*int(kgv/nenner_2))+"/"+str(kgv)
            variable = [ganz,str(bruch_1), zeichen, str(bruch_2), kgv, int(kgv/nenner_1), int(kgv/nenner_2)]
            lsg = [str(bruch_lsg),ungekuerzt,str(bruch_lsg)]
            pro_text = frage = "{}{}{}{}="
            lsg += ["indiv_0", "indiv_1"]
            # grafik:
            radius = 60
            center_y = 60
            center_x = 100
            center_x2 = 250
            parameter = {
                'name': 'svg/winkel.svg',
                'object': 'rechnung',
                'winkel': zaehler_faerben(nenner_1, zaehler_1, "LightSkyBlue"),
                "center_x2" : center_x2,
                'winkel2': zaehler_faerben(nenner_2, zaehler_2, farbe2)
            }
            koordinaten = {
                "center_x": center_x,
                "center_y": center_y,
                "radius": radius,
                "sweep_flag": 1,
                **segment(center_x, center_y, radius, 360/nenner_1),
                **segment(center_x2, center_y, radius, 360/nenner_2, 2),
            }
            if nenner_1 != nenner_2:  
                if stufe%2 == 1:
                    if nenner_1 == kgv:
                        hilfe_id = 31
                        hilfe = "Wenn die Brüche nicht den gleichen Nenner haben, musst du sie zunächst gleichnamig machen.<br>Der gemeinsame Nenner heisst hier {4} - also musst du den zweiten Bruch mit {6} erweitern."
                    elif nenner_2 == kgv:
                        hilfe_id = 32
                        hilfe = "Wenn die Brüche nicht den gleichen Nenner haben, musst du sie zunächst gleichnamig machen.<br>Der gemeinsame Nenner heisst hier {4} - also musst du den ersten Bruch mit {5} erweitern."
                    else:    
                        hilfe_id = 33
                        hilfe = "Wenn die Brüche nicht den gleichen Nenner haben, musst du sie zunächst gleichnamig machen.<br>Der gemeinsame Nenner heisst hier {4} - den ersten Bruch musst du also mit {5} erweitern, den zweiten mit {6}."
                else:
                    if nenner_1 == kgv:
                        hilfe_id = 34
                        hilfe = "Wenn die Brüche nicht den gleichen Nenner haben, musst du sie zunächst gleichnamig machen.<br>Der gemeinsame Nenner heisst hier {4} - also musst du den zweiten Bruch mit {6} erweitern.<br>Vielleicht verstehst du das besser, wenn du dir das Bild nochmal anschaust!"
                    elif nenner_2 == kgv:
                        hilfe_id = 35
                        hilfe = "Wenn die Brüche nicht den gleichen Nenner haben, musst du sie zunächst gleichnamig machen.<br>Der gemeinsame Nenner heisst hier {4} - also musst du den ersten Bruch mit {5} erweitern.<br>Vielleicht verstehst du das besser, wenn du dir das Bild nochmal anschaust!"
                    else:    
                        hilfe_id = 36
                        hilfe = "Wenn die Brüche nicht den gleichen Nenner haben, musst du sie zunächst gleichnamig machen.<br>Der gemeinsame Nenner heisst hier {4} - den ersten Bruch musst du also mit {5} erweitern, den zweiten mit {6}.<br>Vielleicht verstehst du das besser, wenn du dir das Bild nochmal anschaust!"
                    koordinaten.update(segment(center_x, center_y, radius, 360/kgv, 3))
                    parameter['winkel3'] = zaehler_faerben(kgv, 0, "LightSkyBlue")
            parameter.update(koordinaten)
        elif typ <= 4:    	                                                                    # Addition (typ=1) und Subtraktion (typ=2) gleichnamiger Brüche
            nenner = random.randint(3,10)
            zaehler_1 = zaehler_2 = nenner 
            if typ2 == 1:
                typ2 = random.randint(1,7)                                                      # auch gemischte Zahlen
            else:
                typ2 = random.randint(1,5)  
                text="Berechne und kürze (falls möglich):<br><br>{1} {2} {3} ="
                anmerkung="(Für das Kürzen gibt es einen halben Extrapunkt)"
            #typ2=7
            if (typ == 3 and typ2 >=6) or (typ == 4 and typ2 == 7):                             # auch gemischte Zahlen
                while ggt(zaehler_1,nenner)!=1 or ggt(zaehler_2,nenner)!=1:
                    zaehler_1 = random.randint(1, nenner-1)
                    zaehler_2 = random.randint(1, nenner-1) 
            elif typ == 4:
                zaehler_1 = zaehler_2 = 1                                                       # Subtraktion
                while zaehler_1 + zaehler_2 >= nenner or ggt(zaehler_1,nenner)!=1 or ggt(zaehler_2,nenner)!=1 or zaehler_1 <= zaehler_2:
                    nenner = random.randint(3,10)
                    zaehler_1 = random.randint(1, nenner-1)
                    zaehler_2 = random.randint(1, nenner-1)
            else:                                                                               # keine gemischten Zahlen
                while zaehler_1 + zaehler_2 >= nenner or ggt(zaehler_1,nenner)!=1 or ggt(zaehler_2,nenner)!=1:
                    zaehler_1 = random.randint(1, nenner-1)
                    zaehler_2 = random.randint(1, nenner-1)
            bruch_1 = Fraction(zaehler_1/nenner).limit_denominator()
            bruch_2 = Fraction(zaehler_2/nenner).limit_denominator()
            if typ == 3:                                                                        # Addition
                zeichen = "+"
                if typ2 == 7:                                                                    # gemischte Zahl in der Aufgabe
                    ganz = "1 "
                    bruch_lsg = Fraction((zaehler_1+nenner+zaehler_2)/nenner).limit_denominator()
                    ungekuerzt = str(zaehler_1+zaehler_2+nenner)+"/"+str(nenner)
                    anmerkung="(Achtung beim ersten Term handelt es sich um eine gemischte Zahl!)"   
                else:
                    ganz = ""
                    bruch_lsg = Fraction(zaehler_1/nenner+zaehler_2/nenner).limit_denominator()
                    ungekuerzt = str(zaehler_1+zaehler_2)+"/"+str(nenner)
            else:                                                                               # Subtraktion
                zeichen = "-" 
                if typ2 ==7:                                                                    # gemischte Zahl in der Aufgabe
                    ganz = "1 "
                    bruch_lsg = Fraction((zaehler_1+nenner-zaehler_2)/nenner).limit_denominator()
                    ungekuerzt = str(zaehler_1-zaehler_2+nenner)+"/"+str(nenner)
                    anmerkung="(Achtung beim ersten Term handelt es sich um eine gemischte Zahl!)"   
                else:
                    ganz = ""
                    bruch_lsg = Fraction((zaehler_1-zaehler_2)/nenner).limit_denominator()
                    ungekuerzt = str(zaehler_1-zaehler_2)+"/"+str(nenner)
            variable = [ganz,str(bruch_1), zeichen, str(bruch_2)]
            if typ2 >= 6:
                term_a, term_b = gemischte_zahl(bruch_lsg.numerator, bruch_lsg.denominator)
                lsg = [term_a, ungekuerzt, term_b]
            else:
                lsg = [str(bruch_lsg),ungekuerzt,str(bruch_lsg)]
            pro_text = frage = "{}{}{}{}="
            lsg += ["indiv_0", "indiv_1"]
            wert = parser.evaluate(lsg[2],{})
            wert = 0.5
            if typ2 == 7:
                variable.append(nenner)
                hilfe_id = 13
                hilfe = "Anstelle der 1 kannst du hier einfach noch {4}/{4} addieren."
            elif wert <= 1:
                hilfe_id = 11
                hilfe = "Gleichnamige Brüche werden addiert bzw. subtrahiert, indem man die Zähler addiert bzw. subtrahiert. Der Nenner bleibt unverändert.<br>(Vergiss nicht zu überprüfen, ob man das Ergebnis kürzen kann.)"
            else:
                hilfe_id = 12
                hilfe = "Gleichnamige Brüche werden addiert bzw. subtrahiert, indem man die Zähler addiert bzw. subtrahiert. Der Nenner bleibt unverändert.<br>Hier kannst du das Ergebnis noch in eine gemischte Zahl umwandeln.<br>(Vergiss nicht zu überprüfen, ob man das Ergebnis kürzen kann.)"
            parameter = {'name':'normal'}
        else:
            bruch_1, bruch_2 = brueche_erzeugen(15)
            nenner_1 = bruch_1.denominator                                                      # hier werden die beiden Brüche gekürzt
            nenner_2 = bruch_2.denominator
            zaehler_1 = bruch_1.numerator 
            zaehler_2 = bruch_2.numerator
            if typ == 5:
                zeichen = "·"
                bruch_lsg = bruch_1*bruch_2
                ungekuerzt = str(zaehler_1*zaehler_2)+"/"+str(nenner_1*nenner_2)
                hilfe_id = 51
                hilfe = "Das ist ganz einfach: Du musst nur die beiden Zähler multiplizieren und ebenso die beiden Nenner."
            else:            
                zeichen = ":"
                bruch_lsg = bruch_1/bruch_2
                ungekuerzt = str(zaehler_1*nenner_2)+"/"+str(nenner_1*zaehler_2)
                if stufe%2 == 1:
                    hilfe_id = 61
                    hilfe = "Du musst den ersten Bruch mit dem Kehrwert des zweiten Bruchs multiplizieren."
                else:
                    hilfe_id = 62
                    hilfe = "Du musst den ersten Bruch mit dem Kehrwert des zweiten Bruchs multiplizieren.<br>Das heißt, du musst vor dem Multiplizieren den Zähler und den Nenner vom zweiten Bruch vertauschen."
            variable = [ganz,str(bruch_1), zeichen, str(bruch_2)]
            term_a, term_b = gemischte_zahl(bruch_lsg.numerator, bruch_lsg.denominator)
            lsg = [term_a, ungekuerzt, term_b]
            pro_text = frage = "{}{}{}{}="
            lsg += ["indiv_0", "indiv_1"]
            parameter = {'name':'normal'}
        return typ, typ2, titel, text, pro_text, frage, variable, einheit, anmerkung, lsg, hilfe_id, erg, parameter

def quader(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "":                                                               
        typ_anf = 3
        typ_end = 7
        if "Oberfläche" in optionen or jg >= 7:
            if stufe%2 == 1 or jg > 8:
                typ_anf = -1
            else:
                typ_anf = 2
        return typ_anf, typ_end
    elif eingabe != "":
            loe = (lsg[1])
            eing = eingabe.replace(",",".")
            try: 
                if float(eing) == float(loe):
                    return 1, ""
                else:
                    return 0, "" 
            except:
                return 1, ""
    else:                                                                            
        typ = random.randint(typ_anf, typ_end) 
        pro_text = frage = einheit = anmerkung = hilfe = ""
        hilfe_id = 0
        variable = {}
        erg = None 
        einheiten_liste = ['mm', 'cm', 'm', 'dm']
        einheit = random.choice(einheiten_liste)
        a = random.randint(2,5)
        if     typ == 2 or typ == 4:                                        # Quader
            titel = "Quader"
            b = random.randint(2,5)
            c = random.randint(2,5)
            einheit_frage = einheit
            if typ == 2:                                                           # O Quader
                zeichen = "0"
                gesucht = "<b>die Oberfläche</b>"
                anmerkung = "Du sollst beim Rechentrainer keinen Taschenrechner benutzen.<br>Wenn du diese Rechnung nicht im Kopf ausrechnen kannst, kannst du hier einfach die Rechnung so eintippen, wie du sie auch in einen Taschenrechner eintippen würdest."
                einheit = einheit + "²"                    
                wert = 2*(a*b+a*c+b*c)
                term = "2*(" + str(a) + "*"+ str(b) + " + " + str(a) + "*"+ str(c) + " + "+ str(b) + "*"+ str(b) + ")"
                lsg = [term + "=" + str(wert), wert, "indiv_2"]
                if stufe%2 == 1:
                    hilfe_id = 31
                else:
                    hilfe_id = 32
            else:                                                                  # V Quader
                zeichen = "V"
                gesucht = "das Volumen"
                einheit = einheit + "³"
                erg = a*b*c
                if stufe%2 == 1:
                    hilfe_id = 11
                else:
                    hilfe_id = 12
                lsg = [str(erg)+einheit]
            text = "Berechne {4} eines Quaders mit<br>a={0}{3}, b={1}{3} und c={2}{3}!"
            pro_text = "{5} Quader {0}·{1}·{2}"
            frage = "{5}="
            variable = [a, b, c, einheit_frage, gesucht, zeichen]
            parameter = {'name':'normal'}
        elif   typ == 5 or typ == -1:                                       # Quader mit Grafik                      
            titel = "Quader"
            anmerkung= "Alle Angaben in mm"
            breite_u = random.randint(2,4)*20
            breite_o = breite_u 
            hoehe = random.randint(1,4)*50
            tiefe = random.randint(1,2)*100
            breite_u_text = a = int(breite_u/5)
            tiefe_text = b = int(tiefe/10)
            hoehe_text = c = int(hoehe/10)
            einheit = "mm³"
            if typ == 5:
                gesucht = "das Volumen"
                frage = "V="
                erg = breite_o*hoehe*tiefe/500
                lsg = [str(int(erg))]
            else:
                gesucht = "<b>die Oberfläche</b>"
                einheit = "cm²"
                frage = "O="
                anmerkung = "Du sollst beim Rechentrainer keinen Taschenrechner benutzen.<br>Wenn du diese Rechnung nicht im Kopf ausrechnen kannst, kannst du hier einfach die Rechnung so eintippen, wie du sie auch in einen Taschenrechner eintippen würdest."
                wert = 2*(a*b+a*c+b*c)
                term = "2*(" + str(a) + "*"+ str(b) + " + " + str(a) + "*"+ str(c) + " + "+ str(b) + "*"+ str(b) + ")"
                lsg = [term + "=" + str(wert), wert, "indiv_2"]
                if stufe%2 == 1:
                    hilfe_id = -11
                else:
                    hilfe_id = -12
            text = "Berechne {4} dieses Quaders!"
            pro_text = "{} Quader {}·{}·{}"
            variable = [frage,a,b,c,gesucht]
            einheit = "mm³"
            typ3,  hilfe2 , anmerkung2, lsg2, parameter = sub_koerper(-1, breite_u, breite_o, hoehe, tiefe, 0, hoehe*2+tiefe*0.5)  # erstellt die Grafik
            parameter2 = {'breite_o': breite_o*2, 'breite_u': breite_u*2, 'hoehe': hoehe, 'tiefe': math.sqrt(2*(tiefe*0.35)**2), 'breite_o_text': int(breite_o/5), 'breite_u_text': breite_u_text, 'hoehe_text': str(hoehe_text).replace(".",","), 'tiefe_text': int(tiefe/10)}
            parameter.update(parameter2)
        elif   typ == 3 or typ == 6:                                        # Würfel
            titel = "Würfel"
            einheit_frage = einheit
            if typ == 3:                                                            # O Würfel
                gesucht = "<b>die Oberfläche</b>"
                zeichen = "0"
                einheit = einheit + "²"
                erg = 6*a**2
                if stufe%2 == 1:
                    hilfe_id = 21
                else:
                    hilfe_id = 22
            else:                                                                   # V würfel
                gesucht = "das Volumen"
                zeichen = "V"
                einheit = einheit + "³"
                erg = a**3
                if stufe%2 == 1:
                    hilfe_id = 41
                    einheit_lsg = einheit + "³"
                else:
                    hilfe_id = 42
            text = "Berechne {2} eines Würfels mit einer Kantenlänge von {0}{1}!"
            pro_text = "{3} Würfel a={0}{1}"
            frage = "{3}="
            variable = [a, einheit_frage, gesucht, zeichen]
            lsg = [str(erg)+einheit]
            parameter = {'name':'normal'}
        elif   typ == 1 or typ == 7:                                        # räumliches Vorstellungsvermögen
            titel = "zusammengesetzte Körper"
            anzahl_breite = random.randint(3,4)
            anzahl_tiefe = random.randint(3,4)
            anzahl_hoehe = random.randint(3,4)
            fehlt = random.randint(1,2)
            top_ebene = [
                [
                    (t >= anzahl_tiefe - fehlt)
                    or (h >= anzahl_breite - fehlt )
                    for h in range(anzahl_breite)
                ] for t in range(anzahl_tiefe)
            ]
            full_plane = [[False] * anzahl_breite] * anzahl_tiefe
            schieb_positionen = [
                (50 + h * 20 - t * 6, t * 6 - v * 20 + anzahl_hoehe*20 - 20)
                for v, plane in enumerate([full_plane] * (anzahl_hoehe - 2) + [top_ebene])
                for t, row in enumerate(plane)
                for h, kein in enumerate(row)
                if not kein
            ]
            zaehler = 0
            for n in top_ebene:
                for m in n:                    
                    if m == False:
                        zaehler +=1
            oberflaeche = [0,4,6,8,8,12,10,16,12,12]
            mantel = oberflaeche[zaehler]
            variable = [len(schieb_positionen)]
            if typ == 7:                                                            # Volumen
                text = "Jedes dieser Würfelchen hat eine Kantenlänge von 1cm.<br>Berechne das Volumen dieses zusammengesetzten Körpers!"
                pro_text = "V von {} Würfelchen"
                frage = "V="
                einheit = "cm³"
                hilfe_id = 71
                erg = len(schieb_positionen)
                lsg = [str(erg)]
            else:                                                                   # Oberfläche
                text = "Jedes dieser Würfelchen hat eine Kantenlänge von 1cm.<br>Berechne <b>die Oberfläche</b> dieses zusammengesetzten Körpers!"
                pro_text = "O von {} Würfelchen"
                anmerkung = "Du kannst anstelle des Ergebnisses auch deine Rechnung (wie in einem Taschenrechner) eingeben."
                einheit = "cm²"
                frage = "O="
                hilfe_id = 72
                wert = 2*((anzahl_breite+anzahl_tiefe)*(anzahl_hoehe-2)+anzahl_breite*anzahl_tiefe)+mantel
                term = "2*((" + str(anzahl_breite) + "+" + str(anzahl_tiefe) + ")*" + str(anzahl_hoehe-2) + "+" + str(anzahl_breite) + "*" + str(anzahl_tiefe) + ")+" + str(mantel)
                lsg = [term + "=" + str(wert), wert, "indiv_2"]
            parameter = {'name': 'svg/geometrie.svg', 'object': 'zusammengesetzt',
                'box_hoehe' : anzahl_hoehe * 20 + anzahl_tiefe * 8,
                'box_breite' : 300,             
                'schieb': schieb_positionen,
            } 
        else:      # elif   typ == 8 or typ == 9 or typ == 0:               # Prismen
            titel = "Prismen"
            anmerkung= "Alle Angaben in cm"
            if typ == 8:                                                                   # trapezförmig
                breite_o = breite_u = 1
                while breite_o >= breite_u-5:
                    breite_u = random.randint(2,4)*20
                    breite_o = random.randint(1,3)*20
            else:                                                            # dreieckige Grundfläche                                                             
                breite_u = random.randint(2,4)*20
                breite_o = 0   
            tiefe = random.randint(1,2)*100
            if typ == 0:
                einheit = "cm²"
                breite_u_text = int(breite_u/5)
                tiefe_text = int(tiefe/10)
                hoehe = math.sqrt((2*breite_u)**2-((breite_u)**2))
                hoehe_text = round((hoehe/10),1)
                typ2 = random.randint(1,2)
                if typ2 == 1:                                                        # Oberfläche
                    text = "Berechne die Oberfläche dieses Prismas - die Grundfläche ist ein <b>gleichseitiges</b> Dreieck!"
                    pro_text = "O Prisma "
                    frage = "O="
                    anmerkung = "Du sollst beim Rechentrainer keinen Taschenrechner benutzen.<br>Da du diese Rechnung nicht im Kopf ausrechnen kannst, kannst du hier einfach die Rechnung eintippen, wie du sie auch in einen Taschenrechner eintippen würdest."
                    wert = 3*breite_u_text*tiefe_text+breite_u_text*hoehe_text
                    term = "((3 * " + str(breite_u_text)+") * " + str(tiefe_text) + ") + (" + str(breite_u_text) + " * " + str(hoehe_text) + ")"
                else:                                                               # Mantelfläche
                    text = "Berechne die <b>Mantelfläche</b> dieses Prismas - die Grundfläche ist ein <b>gleichseitiges</b> Dreieck!"
                    pro_text = "M Prisma "
                    frage = "M="
                    if stufe%2 == 1:
                        hilfe_id = 1
                    else:
                        hilfe_id = 2
                        hilfe = "Mantelfläche = Umfang mal Körperhöhe (nicht Höhe des Dreiecks!)<br>M = u · k = (3 · 16)  · 20"                         
                    wert = 3*breite_u_text*tiefe_text
                    term = "(3 * " + str(breite_u_text)+") * " + str(tiefe_text)
                lsg = [term + "=" + str(round(wert,1)), round(wert,1), "indiv_2"]            
            else:
                text = "Berechne das Volumen dieses Prismas!"
                frage = "V="
                einheit = "cm³"
                hoehe = random.randint(5,6)*20
                erg = (breite_o+breite_u)/2*hoehe*tiefe/500
                lsg = [str(int(erg))]
                hoehe_text = int(hoehe/10)
            typ3,  hilfe2, anmerkung2, lsg2, parameter = sub_koerper(-1, breite_u, breite_o, hoehe, tiefe, 0, hoehe*2+tiefe*0.5)  # erstellt die Grafik
            parameter2 = {'breite_o': breite_o*2, 'breite_u': breite_u*2, 'hoehe': hoehe, 'tiefe': math.sqrt(2*(tiefe*0.35)**2), 'breite_o_text': int(breite_o/5), 'breite_u_text': breite_u_text, 'hoehe_text': str(hoehe_text).replace(".",","), 'tiefe_text': int(tiefe/10)}
            parameter.update(parameter2)
        return typ, 0, titel, text, pro_text, frage, variable, einheit, anmerkung, lsg, hilfe_id, erg, parameter

def zuordnungen(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "":
        typ_anf = 2
        typ_end = 8
        if stufe >= 6 or jg >= 7 or "anti" in optionen:
            typ_anf = 1
            typ_end = 11
        return typ_anf, typ_end
    else:
        if aufgnr == 1:
            if typ_anf == 2:
                typ = 2 
            else:
                typ = random.randint(1,2)
        else:
            typ = random.randint(3, typ_end) 
        titel = "Zuordnungen" 
        text = "default{}"
        pro_text = ""
        variable = []
        frage = ""
        einheit = ""
        anmerkung = ""
        hilfe_id = 0
        erg = None
        parameter = {'name':'normal'}
        if typ == 1:                                                    # Tabelle antiproportional
            text = "Ergänze diese Tabelle zur antiproportionalen Zuordnung"
            zahl1 = random.randint(1, 5) * 30
            pro_text = "Tabelle Prop.konstante: " + format_zahl(zahl1)
            if stufe%2 == 0:
                zahlen = [2,1,3,4]
            else:
                zahlen = [2,3,4,5]
            lsg = []
            x_werte = {}
            y_werte = {}
            for n in zahlen[1:]:                                # berechnet die Lösungen
                lsg.append(format_zahl(zahl1/n, 2))
            for n in range (1,5):
                x_werte["x" + str(n)] = zahlen[n-1]
                y_werte["y" + str(n)] = format_zahl(zahl1/zahlen[n-1],2)
            parameter = {'name': 'tab_antiprop', 'titel_x': 'Teile', 'titel_y': 'Preis', 'x0': '[Anzahl]', 'y0': '[Euro]'}
            parameter.update(x_werte)
            parameter.update(y_werte) 
            hilfe_id = 10 + stufe%2
        elif typ == 2:                                                  # Tabelle proportional
            text = "Ergänze diese Tabelle zur proportionalen Zuordnung"
            zahl1 = random.randint(1, 5) * random.randint(1, 12)*0.1
            pro_text = "Tabelle Prop.faktor: " + format_zahl(zahl1)
            if stufe%2 == 0:
                zahlen = [2,1,3,4]
            else:
                zahlen = [2,3,4,5]
            lsg = []
            x_werte = {}
            y_werte = {}
            for n in zahlen[1:]:                                # berechnet die Lösungen
                lsg.append(format_zahl(zahl1*n, 2))
            for n in range (1,5):
                x_werte["x" + str(n)] = zahlen[n-1]
                y_werte["y" + str(n)] = format_zahl(zahlen[n-1]*zahl1,2)
            parameter = {'name': 'tab_prop', 'titel_x': 'Teile', 'titel_y': 'Preis', 'x0': '[Anzahl]', 'y0': '[Euro]'}
            parameter.update(x_werte)
            parameter.update(y_werte)
            hilfe_id = 20 + stufe%2
        elif typ <= 4:                                                  # prop. Preis mit Komma
            zahl3 = random.randint(1,15)*10/100
            zahl1 = random.randint(1,10)
            zahl2=zahl1
            while zahl1 == zahl2:
                zahl2 = random.randint(2,11)
            erg = zahl2*zahl3
            lsg = format_zahl(erg)+"€"
            text="Wenn {2} Dings {1} Euro kosten, wie viel kosten dann {3} Dings?"
            variable = ['Ding kostet', format_zahl(zahl3*zahl1), zahl1, zahl2]
            frage = "{} kosten".format(zahl2)
            einheit = "Euro"
            hilfe_id = 30
        elif typ <= 8:                                                  # prop. Euro und Gramm, ganzzahlig
            typ2 = random.randint(1,6)
            if typ2 <= 3:                                               # Gramm
                text_bst = ["Ding wiegt", "g" , "Gramm", "wiegen"]
            if typ2 <=2:                                                # gramm mal 5 bzw 10
                typ2 *= 5
            else:
                typ2 = 1
                text_bst = ["Ding kostet", "€" , "Euro", "kosten"]           
            zahl3 = random.randint(1,10)*typ2                           # multipliziert mit 1, 5 bzw. 10
            zahl1 = random.randint(2,10)
            zahl2=zahl1
            while zahl1 == zahl2:
                zahl2 = random.randint(2,11)
            erg = zahl2*zahl3
            lsg = str(erg) + text_bst[1]
            text="Wenn {2} Dings {1} {4} {5}, wie viel {5} dann {3} Dings?"
            variable = [text_bst[0], zahl3*zahl1, zahl1, zahl2, text_bst[2], text_bst[3]]
            frage = "{} {}".format(zahl2, text_bst[3])  
            einheit = text_bst[2]
            hilfe_id = 30
        else:                                                           #antiprop.
            if typ == 8:
                typ2 = random.randint(1,5)*0.5
                zahl1 = random.randint(2,8)
                zahl2=zahl1
                while zahl1 == zahl2:
                    zahl2 = random.randint(1,5)*0.5
                zahl3 = int(random.randint(1,3)*zahl2*2)
                erg = int(zahl1*zahl3/zahl2)
                text="Wenn man {1} Liter Wasser am Tag verbraucht, reicht der Vorrat für {0} Tage. Wie lange reicht er bei einem Verbrauch von {2} Litern am Tag?"
                pro_text = "antiprop. Wasservorrat: {}*{}/{}".format(format_zahl(zahl1,1), zahl3, format_zahl(zahl2,1))
                variable = [zahl3, format_zahl(zahl1,1), format_zahl(zahl2,1), ]
                frage = "Er reicht für"
                einheit = "Tage"
                hilfe_id = 100 + stufe%2
                lsg = str(erg)+"Tage"
            else:
                typ2 = random.randint(0,3)
                zahl1 = random.randint(2,8)
                zahl2=zahl1
                while zahl1 == zahl2:
                    zahl2 = random.randint(2,5)
                zahl3 = random.randint(1,3)*zahl2
                erg = int(zahl1*zahl3/zahl2)
                if typ == 9:
                    text="Mit einem Stapel Wertchips können {1} Leute {0}  mal schobeln, wie oft können {2} Leute damit schobeln?"
                    pro_text = "antiprop. schobeln: {}*{}/{}".format(zahl1, zahl3, zahl2)
                    variable = [zahl3, zahl1, zahl2, ]
                    frage = "Sie können"
                    einheit = "mal schobeln"
                    anmerkung = "(Ich habe auch keine Ahnung, was schobeln bedeutet - es handelt sich aber um eine antiproprtionale Zuordnung)"
                    hilfe_id = 120 + stufe%2
                    lsg = str(erg)+"mal"
                else:
                    txt_bst1 = ["die Lebensmittel", "der Futtervorrat"]
                    txt_bst2 = ["ein Passagier", "ein Tier", "ein Gast", "ein Pferd"]
                    txt_bst3 = ["reichen", "reicht"]
                    txt_bst4 = ["Passagiere", "Tiere", "Gäste", "Pferde"]
                    txt_bst5 = ["sie", "er"]
                    text="Wenn {0} für {4} {6} {3} Tage lang {2}, wie lange {2} {7} dann für {5} {6}?"
                    pro_text = "antiprop. {}: {}*{}/{}".format((txt_bst1[typ2%2])[4:], zahl1, zahl3, zahl2)
                    variable = [txt_bst1[typ2%2], txt_bst2[typ2], txt_bst3[typ2%2], zahl3, zahl1, zahl2, txt_bst4[typ2],txt_bst5[typ2%2]]
                    frage = "Er reicht für"
                    einheit = "Tage"
                    lsg = str(erg)+"Tage"
                    hilfe_id = 110 + stufe%2
        return typ, typ2, titel, text, pro_text, frage, variable, einheit, anmerkung, [lsg], hilfe_id, erg, parameter

def prozentrechnung(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "": 
        typ_anf = 1
        typ_end = 4
        if stufe >= 28 or "Zins" in optionen:
            if stufe%1>1:               # nur A-Kurs
                typ_end = 20
            else:
                typ_end = 18
        elif jg >= 9:
            typ_end = 20
        else:
            if stufe >= 22 or "vermindert" in optionen:
                if stufe%2==0:
                    typ_end = 13
                else:
                    typ_end = 14
            elif stufe >= 20 or "Prozentsatz" in optionen:
                if stufe%2==0:
                    typ_end = 11
                else:
                    typ_end = 12
            elif stufe >= 18 or "Prozentwert" in optionen:
                typ_end = 8
        return typ_anf, typ_end
    elif eingabe != "":
        if typ == 1:
            parser = Parser()
            try:
                zahl=round(parser.parse(eingabe.replace(",",".").replace(":","/")).evaluate({}),3)
                loe = round(parser.parse(lsg[0].replace(":","/")).evaluate({}),3)
                if loe == zahl:
                    if typ == 1:
                        return 0, "Das Ergebnis ist noch nicht sinnvoll gekürzt"
                return -1, ""
            except:
                return -1, ""
        elif typ == 2:                                                    # Kreise schätzen
            wert = int((lsg[1])*100)
            if abs(wert-int(eingabe)) < 5: 
                if wert in (25,50,75):
                    return -1, "Den Wert will ich genau wissen!"
                else:
                    return 1, " Genauer wäre " + str(int(lsg[1]*100)) + "%" 
            else:
                return -1, ""             
        elif typ in (14,16):
            loe = lsg[1]
            if eingabe.isdigit:
                try:
                    if float(eingabe.replace(",",".")) == float(loe):                       # überprüfen, ob der Wert steimmt (z.B. Kommazahl eingegeben)
                        return 1, ""
                    else:
                        return -1, ""
                except: 
                    parser = Parser()
                    try:
                        zahl=round(parser.parse(eingabe.replace(",",".").replace(":","/")).evaluate({}),3)
                        if float(loe) == zahl:
                            return 1, ""
                        else:
                            return -1, ""
                    except:
                        return 0, "Da stimmt was nicht - den Term kann ich nicht berechnen"
            return -1, ""
        else:
            loe = (lsg[1])
            eing = eingabe.replace(",",".")
            try: 
                if float(eing) == float(loe):
                    return 1, "<br><b>Aber:</b> Du sollst das Ergebnis nicht ausrechnen, sondern den Lösungsweg eintippen!<br><b>Du sollst beim Rechentrainer auch keinen Taschenrechner benutzen!</b>"
                else:
                    return -1, "" 
            except:
                return 1, ""
    else:                                                                            
        typ = random.randint(typ_anf, typ_end)
        typ2 = 0
        titel = "Prozentrechnung" 
        parameter = {'name': 'normal',} 
        pro_text = einheit = anmerkung = ""
        hilfe_id = 0
        hilfe_text = []
        erg = None 
        prozent_liste=[0.50,0.25,0.10,0.20,0.75,0.90,  0.30,0.40,0.60,0.80,  0.05,0.125]
        #für E-Kurs', für G-Kurs bis 6, A-Kurs alle:
        if typ >= 14:                         
            prozent=random.choice(prozent_liste[:3])
            #if typ == 14:
             #   prozent = prozent + 1
        elif stufe%2 == 0 or typ ==3 or typ == 4:                         
            prozent=random.choice(prozent_liste[:6])    
        elif stufe%1 == 0:                         
            prozent=random.choice(prozent_liste[:10])  
        else:                                       # diese kommen nur bei A-Kurs oder Gymnasium
            prozent=random.choice(prozent_liste)
        bruch = Fraction(prozent).limit_denominator()
        if (prozent*100)%1>0.001:
            str_prozent = str(round(prozent*100,1))
        else:
            str_prozent = str(int(prozent*100))  
        if typ >= 8 and typ < 15:
            einh = ["Euro", "€", "m", "kg",""]
            einheit = random.choice(einh)
            if typ in (8,10,12): 
                anmerkung="Du sollst nicht das Ergebnis ausrechnen, sondern den Term für die Rechnung angeben!" 
                frage = "Rechnung:"  
                zahl1 = 5
                while zahl1%5==0: 
                    zahl1 = random.randint(2,100)
                zahl2 = 10
                while zahl2%10==0: 
                    zahl2 = random.randint(2,100)
                variable = [zahl1, zahl2, einheit]
            else:
                zahl1 = random.randint(1,5)*5
        if   typ == 1:                              # Prozentsatz als Bruch
            anmerkung = "(Bsp. 70%=7/10)"
            prozent=int(prozent*100)
            ggt = gcd(int(prozent),100)
            variable = [prozent]
            text = "Gib als (sinnvoll) gekürzten Bruch an: {}%"
            pro_text = "{}% als Bruch"
            frage = "{}%≙"
            lsg = [str(bruch)]
            if bruch.numerator == 1:
                hilfe_id = 11
                hilfe_text = [str(bruch)]
            else:
                hilfe_id = 12
                hilfe_text = [ggt]
                if ggt == 20:
                    hilfe_id = 13
            if prozent%10 == 0:
                lsg.append(str(int(prozent/10))+"/10")
            lsg.append("indiv_0")
            #context = dict(parameter = parameter, prozent = prozent*100, bruch = bruch, text = text)
        elif typ == 2:                              # Prozentsatz aus Kreis
            winkel = prozent*360  
            center_x = 150 
            center_y = 60
            radius = 60 
            text = "{} dieses Kreises sind blau gefärbt. Wie viel Prozent entspricht das?"
            pro_text = "{} in Prozent"
            variable = [str(bruch),]
            frage = "{}≙"
            einheit = "%"
            erg=prozent*100
            lsg = [str_prozent+"%", prozent, "indiv_0"]
            if stufe%2 == 0:
                if bruch.denominator%2 == 0:
                    hilfe_id = 21
                elif prozent == 0.9:
                    hilfe_id = 22
                elif prozent == 0.8:
                    hilfe_id = 23
                elif prozent == 0.7:
                    hilfe_id = 24
                elif prozent == 0.6:
                    hilfe_id = 25
                elif prozent == 0.4:
                    hilfe_id = 26
                elif prozent == 0.3:
                    hilfe_id = 27
                elif prozent == 0.2:
                    hilfe_id = 28
                elif prozent == 0.1:
                    hilfe_id = 29
                else:
                    hilfe_id = 20
            parameter = {'name': 'svg/winkel.svg', 'object': 'segment', 'color': 'blue'}
            koordinaten = dict(center_x = center_x, center_y = center_y, radius = radius, sweep_flag = 1)
            koordinaten1 = segment(center_x, center_y, radius, winkel)
            koordinaten.update(koordinaten1)
            parameter.update(koordinaten)
        elif typ <= 4:                              # Prozentsatz aus Rechteck
            zeile=2
            spalte=1
            while zeile>spalte or farbe<1 or (farbe%spalte>0 and farbe%zeile>0):
                zeile = random.randint(3,7)
                spalte = random.choice([3, 4, 5, 10])
                farbe = zeile*spalte*prozent
            farbe = int(farbe) 
            koordinaten = []
            if typ == 3:
                blau = [1] * farbe + [0] * (spalte * zeile - farbe)
                for y in range(zeile):
                    for x in range(spalte):
                        if farbe%spalte==0:
                            index = y * spalte + x
                        else:
                            index = x * zeile + y
                        if index < len(blau) and blau[index]:
                            koordinaten.append((x * 15, y * 15, 1))
                        else:
                            koordinaten.append((x * 15, y * 15, 0))
                text = "Wie viel Prozent der {1} Kästchen in diesem Rechteck sind blau gefärbt?"
                pro_text = "{} von {} Kästchen"
                variable = [farbe, zeile*spalte]
                hilfe_id = 32
                erg=prozent*100
                lsg = [str_prozent+"%", str_prozent]
                einheit = "%"
            else:
                for y in range(zeile):
                    for x in range(spalte):
                        if farbe%spalte==0:
                            index = y * spalte + x
                            hilfe_text = [str_prozent,str(bruch),spalte]
                            hilfe_id = 33
                        else:
                            index = x * zeile + y
                            hilfe_text = [str_prozent,str(bruch),zeile]
                            hilfe_id = 34
                        koordinaten.append((x * 15, y * 15, 0))
                text = "Wie viele der {1} Kästchen müsstest du färben, wenn {0}% in diesem Rechteck blau gefärbt werden sollen?"
                pro_text = "{}% von {} Kästchen"
                variable = [int(prozent*100), zeile*spalte]
                erg = farbe
                lsg = [str(erg)]
                einheit = "müssten gefärbt werden"
            frage = ""
            parameter = {'name': 'svg/winkel.svg', 'object': 'kaestchen', 'schieb': koordinaten,} 
        elif typ <= 7:                              # Prozentwert
            text = "Wie viel sind {}% von {}{}?" 
            frage = "p=" 
            if typ == 5:
                zahl1 = random.randint(1,34)
                zahl2 = random.randint(1,4)
                g = zahl2*100
                variable = [zahl1, g, einheit]
                erg = zahl1*zahl2
                if g != 100:
                    hilfe_id = 51
            else:
                zahl1 = random.randint(1,5)*5
                g = zahl1*bruch.denominator
                variable = [str_prozent, g, einheit]
                erg = zahl1*bruch.numerator
                if g != 100:
                    if bruch.numerator == 1:
                        hilfe_id = 61
                        hilfe_text = [str(bruch), bruch.denominator]
                    else:
                        hilfe_id = 62
                        hilfe_text = [str(bruch), bruch.denominator, bruch.numerator]
            lsg = [str(int(erg))+einheit,str(int(erg))]  
        elif typ == 8:                              # Term für Prozentwert 
            text = "Wie berechnet man {}% von {}{}?"
            frage = "p="
            lsg = [str(zahl2)+"/100*"+str(zahl1),]
            if stufe%2==0:
                hilfe_id = 81
            else:
                hilfe_id = 82
        elif typ == 9:                              # Grundwert
            text = "{}% sind {}{} - Berechne den Grundwert!" 
            pro_text = "{}% sind {}{} - G=?" 
            frage = "G=" 
            variable = [str_prozent, zahl1*bruch.numerator, einheit]
            erg = zahl1*bruch.denominator
            lsg = [str(int(erg))+einheit,str(int(erg))]  
            if stufe%2==0:
                if bruch.numerator == 1:
                    hilfe_id = 91
                    hilfe_text = [str(bruch), bruch.denominator]
                else:                           
                    hilfe_id = 92
                    hilfe_text = [str(bruch), bruch.numerator, bruch.denominator]
            else:
                hilfe_id = 93
                hilfe_text = [str(bruch)]
        elif typ == 10:                             # Term für Grundwert
            text = "{}% sind {}{} - Berechne den Grundwert!" 
            pro_text = "{}% sind {}{} - G=?" 
            frage = "G=" 
            lsg = [str(zahl2)+"/"+str(zahl1)+"*100",]
            if stufe%2==0:
                hilfe_id = 101
            else:
                hilfe_id = 102
        elif typ == 11:                             # Prozentsatz
            text = "Wie viel Prozent sind {0}{2} von {1}{2}?" 
            pro_text = "{} von {}{} - p%=?" 
            frage = "p=" 
            variable = [zahl1*bruch.numerator, zahl1*bruch.denominator, einheit]
            erg = prozent*100
            lsg = [str(int(erg)),str(int(erg))]
            ggt = gcd(zahl1*bruch.numerator, zahl1*bruch.denominator)
            hilfe_id = 111
            hilfe_text = [ggt]
        elif typ == 12:                             # Term für Prozentsatz - nicht für G-Kurs im 8.Sj.
            text = "Wie viel Prozent sind {0}{2} von {1}{2}?" 
            pro_text = "{} von {}{} - p%=?" 
            frage = "p=" 
            zahl1 = zahl2 = 10
            while zahl1 >= zahl2 or zahl1%5==0 or zahl2%10==0: 
                zahl1 = random.randint(2,100)
                zahl2 = random.randint(2,100)
            variable = [zahl1, zahl2, einheit]
            lsg = [str(zahl1)+"/"+str(zahl2)+"*100",]  
            if stufe%2==0:
                hilfe_id = 121
            else:
                hilfe_id = 122
            einheit = "%"
        elif typ == 13:                             # P bei erhöhter und verminderter Grundwert
            if stufe%2==0:
                typ2 = random.randint(1,2)
            else:
                typ2 = random.randint(1,4)
            einheit = "€"
            zahl1 = random.randint(1,5)*5
            if typ2 == 1:                           # erhöhter Grundwert                          
                text = "Eine Ware wird wird um {}% teurer.<br>Vorher kostete sie {}€<br>Wie hoch ist der neue Preis?" 
                pro_text = "{}€+{}% = ?"
                frage = "G=" 
                g = zahl1*bruch.denominator
                erg = int(g*(1+prozent))
                variable = [str_prozent, int(zahl1*bruch.denominator)]
                hilfe_id = 141
                hilfe_text = [str(prozent+1).replace(".",",")]
            if typ2 == 2:                           # verminderter Grundwert                          
                text = "Eine Ware wird um {}% billiger.<br>Vorher kostete sie {}€<br>Wie hoch ist der neue Preis?"
                pro_text = "{}€-{}% = ?"
                frage = "G=" 
                g = zahl1*bruch.denominator
                variable = [str_prozent, int(g)]
                erg = int(g*(1-prozent)) 
                hilfe_id = 142
                hilfe_text = [str(1-prozent).replace(".",",")]
            lsg =[str(erg)]  
        elif typ == 14:                             # G aus P bei erhöhter und verminderter Grundwert (bis 8.Sj. nur E-Kurs)
            typ2 = random.randint(1,2)
            einheit = "€"
            zahl1 = random.randint(1,5)*5
            if typ2 == 1:                                                
                text = "Nach einer Preiserhöhung um {}%, beträgt der neue Preis {}€?<br>Wie hoch war der ursprüngliche Preis?" 
                pro_text = "G+{}% = {}€ - G=?"
                frage = "G=" 
                p = int(zahl1*(1+prozent)*100)
                term = str(p)+"/"+str(int((1+prozent)*100))+"*100"
                variable = [str_prozent,p,int((1+prozent)*100),str(1+prozent).replace(".",",")]
                wert = zahl1*100
            elif typ2 == 2:                         # G aus P vermindert - nur E-Kurs                         
                text = "Nachdem der Preis um {}% reduziert wurde, beträgt der neue Preis {}€?<br>Wie hoch war der ursprüngliche Preis?" 
                pro_text = "G-{}% = {}{} - G=?"
                frage = "G=" 
                p = int(zahl1*(1-prozent)*100)
                term = str(p)+"/"+str(int((1-prozent)*100))+"*100"
                variable = [str_prozent,p,int((1-prozent)*100),str(1-prozent).replace(".",",")]
                wert = zahl1*100
                anmerkung = "Wenn du das nicht im Kopf rechnen kannst, kannst du auch einen Term zur Berechnung eingeben"
            lsg = [term+"="+str(wert),str(wert),"indiv_0"]
            hilfe_id = 143
        elif typ <= 16:                             # Zinsen 
            titel = "Zinsrechnung"
            kapital_liste = [-20, -15, -10, -5, 1,2,3,4,5,10,20,50,100,200]
            kapital = random.choice(kapital_liste)*1000
            if kapital < 0:
                baustein = "x Festgeld"
                zinsen_liste = [0.25,0.5,0.75,1,1.25,1.5]
                zinsen = random.choice(zinsen_liste)
            elif kapital >= 100000:
                baustein = "eine Hypothek"
                anmerkung = "(Mit einer 'Hypothek' finanziert man einen Hauskauf)"
                vorkomma = random.randint(2,4)
            elif kapital >= 5000:
                baustein = "einen Kredit"
                anmerkung = ""
                vorkomma = random.randint(4,5)
            else:
                baustein = "einen Dispositionskredit"
                anmerkung = "(Einen 'Dispo' nimmt man in Anspruch, wenn man sein Konto 'überzieht')"
                vorkomma = random.randint(8,12) 
            protokoll_baustein = baustein.split()[1]
            if kapital > 0:
                nachkomma = [0,0.5]
                zinsen = vorkomma+random.choice(nachkomma)
                text = "Für {} über {}€ muss man {}% Zinsen im Jahr bezahlen. <br> Wie viel ist das?"
                pro_text = "{3} über {1}€ zu {2}% - Z=?"
            else:
                kapital = -1*kapital
                baustein = ""
                text = "Wenn man {1}€ als Festgeld anlegt, bekommt man {2}% Zinsen im Jahr. <br> Wie viel ist das?"
                pro_text = "{1} als Festgeld zu {2}% - Z=?"
                anmerkung = "('Festgeld' heißt, dass man mit der Bank festlegt, dass man das Geld eine längere Zeit nicht benötigt)"
            anmerkung = anmerkung + "<br>Wenn du das nicht im Kopf rechnen kannst, kannst du auch einen Term zur Berechnung eingeben"
            variable = [baustein, trenner(kapital), zinsen, protokoll_baustein]
            frage = "Z="
            einheit = "€"
            wert = kapital/100*zinsen
            lsg = [str(int(wert)),str(wert),"indiv_0"] 
        elif typ <= 18:                             # Tageszinsen
            titel = "Tageszinsen"
            kapital_liste = [2,3,4,5,10]
            kapital = random.choice(kapital_liste)*1000
            vorkomma = random.randint(3,5)
            nachkomma = [0,0.5]
            zinsen = vorkomma+random.choice(nachkomma)
            if zinsen%1 == 0:
                str_zinsen = str(int(zinsen))
            else:
                str_zinsen = str(round(zinsen,1))
            tage = random.randint(1,30)*10
            text = "Für {} über {}€ muss man {}% Zinsen im Jahr bezahlen. <br>Gib den Term an mit dem man die Tageszinsen für {} Tage berechnen kann!"
            pro_text = "{}, {}€, {}%, {} Tage"
            baustein = "einen Kredit"
            anmerkung = ""
            variable = [baustein, trenner(kapital), str(zinsen).replace(".",","), tage]
            frage = "Z="
            einheit = "€"
            hilfe_id = 171
            wert = kapital/100*zinsen/360*tage 
            lsg = [str(int(kapital))+"/100*"+str_zinsen+"/360*"+str(tage)] 
        else:                                       # Kapital aus Monatszinsen - nur A-Kurs und Gymnasium
            titel = "Zinsrechnung"
            belastung = random.randint(6,15)*100
            zinsen = random.randint(6,9)
            text = "Familie Mayer möchte bei ihrer Bank eine Hypothek für den Kauf einer Eigentumswohnung aufnehmen.<br> Für Zinsen und Tilgung müssen sie dafür mit {}% der Hypothekensumme im Jahr rechnen.<br>Im Monat können sie {}€ dafür aufbringen.<br>Wieviel Geld können sie sich dafür von der Bank leihen?<br>Gib einen Term an, mit dem man dieses berechnen kann!"
            pro_text = "Hypothek zu {} für {}€/mtl - K=?"
            anmerkung = "(Mit einer 'Hypothek' finanziert man einen Haus- oder Wohnungskauf. Mit der Tilgung bezahlt man die Schulden ab.)"
            variable = [zinsen,belastung]
            hilfe_id = 191
            frage = "K="
            einheit = "€"
            wert = belastung*12/zinsen*100
            lsg = [str(belastung)+"*12/"+str(zinsen)+"*100="+str(trenner(wert))+"€"] 
        if typ in (8,10,12) or typ >= 18:        # sorgt dafür, dass überprüft wird, ob anstelle eines Termes der Wert eingegeben wurde
            parser = Parser()
            zahl=round(parser.parse(lsg[0].replace(",",".")).evaluate({}),3)
            lsg.append((zahl))
            lsg.append("indiv_2")                                                         #sorgt dafür, dass die Eingabe nochmals in der Funktion der Aufgabe überprüft wird 
        variable.extend(hilfe_text)
        #hilfe = hilfe.format(*variable)
        return typ, typ2, titel, text, pro_text, frage, variable, einheit, anmerkung, lsg, hilfe_id, erg, parameter

def vorzeichen_zahl(wert, stellen=2, trailing_zeros=True):
    text = f"{wert:+.{stellen}f}".replace(".", ",")
    return text.rstrip(",0") if not trailing_zeros and "," in text else text

def negativ(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "":                                                               
        typ_anf = 1
        typ_end = 13
        return typ_anf, typ_end
    else:                                                                            
        typ = random.randint(typ_anf, typ_end) 
        typ2 = 0
        titel = "Titel" 
        text = "default{}"
        variable = ["",]
        pro_text = frage = einheit = anmerkung = ""
        hilfe_id = 0
        zahl1 = zahl2 = 0 
        while zahl1 == 0:
            zahl1 = random.randint(-20, 20)
        if typ >= 7:
            while zahl2 == 0:  
                zahl2 = random.randint(-4,4)
        else:
            while zahl2 == 0:
                zahl2 = random.randint(-20, 20)
        variable = [vorzeichen_zahl(zahl1,0), vorzeichen_zahl(zahl2,0)]
        if typ in [1, 3, 5, 7, 9, 11, 13]:
            zahl1 = zahl1/10
            if typ in [1, 3, 5]:        
                zahl2 = zahl2/10
                variable = [vorzeichen_zahl(zahl1,1), vorzeichen_zahl(zahl2,1)]
            else:
                variable = [vorzeichen_zahl(zahl1,1), vorzeichen_zahl(zahl2,0)]
        if typ == 1:                                                    # + () Kommazahl
            erg = round(zahl1 + zahl2,1)
            text = "({}) + ({})"
        elif typ == 2:                                                  # + () ganze Zahl
            erg = int(zahl1 + zahl2)
            text = "({}) + ({})"
        elif typ == 3:                                                  # - () Kommazahl 
            erg = round(zahl1 - zahl2,1)
            text = "({}) - ({})"
        elif typ == 4:                                                  # - () ganze Zahl
            erg = int(zahl1 - zahl2)
            text = "({}) - ({})"
        elif typ == 5:                                                  # +/- vereinf. Schreibweise Kommazahl
            erg = round(zahl1 + zahl2,1)
            text = "{}  {}"
            variable = [format_zahl(zahl1,1), vorzeichen_zahl(zahl2,1)]
        elif typ == 6:                                                  # +/- vereinf. Schreibweise  ganze Zahl
            erg = int(zahl1 + zahl2)
            text = "{}  {}"
            variable = [format_zahl(zahl1,0), vorzeichen_zahl(zahl2,0)]
        elif typ == 7:                                                  # * () Kommazahl
            erg = round(zahl1*zahl2,2)
            text = "({}) · ({})"
        elif typ == 8:                                                  # * () ganze Zahl
            erg = int(zahl1*zahl2)
            text = "({}) · ({})"
        elif typ == 9:                                                  # * vereinf. Schreibweise Kommazahl
            erg = round(zahl1*zahl2,2)
            variable = [format_zahl(zahl1,1), format_zahl(zahl2,1)]
            if zahl2 < 0:
                text = "{} · ({})"
            else:
                text = "{} · {}"
        elif typ == 10:                                                 # : () ganze Zahl
            erg = (zahl1)
            text = "({}) : ({})"
            variable = [vorzeichen_zahl(zahl1*zahl2,0), vorzeichen_zahl(zahl2,0)]
        elif typ == 11:                                                 # : () Kommazahl
            erg = (zahl1)
            text = "({}) : ({})"
            variable = [vorzeichen_zahl(zahl1*zahl2,1), vorzeichen_zahl(zahl2,0)]
        elif typ == 12:                                                 # : vereinf. Schreibweise ganze Zahl
            erg = zahl1
            variable = [format_zahl(zahl1*zahl2,0), format_zahl(zahl2,0)]
            if zahl2 < 0:
                text = "{} : ({})"
            else:
                text = "{} : {}"
        elif typ == 13:                                                 # : vereinf. Schreibweise Kommazahl 
            erg = zahl1
            variable = [format_zahl(zahl1*zahl2,1), format_zahl(zahl2,0)]
            if zahl2 < 0:
                text = "{} : ({})"
            else:
                text = "{} : {}"
        if typ in [1, 2, 5, 6]:
            if zahl1*zahl2 > 0:
                if zahl1>0:
                    hilfe_id = 12
                else:
                   hilfe_id = 13
            else:
                if zahl1+zahl2 > 0:
                    hilfe_id = 15
                else:
                    hilfe_id = 16
        elif typ in [3, 4]:
            if zahl1*zahl2 < 0:
               hilfe_id = 32
               if erg > 0:
                   hilfe_id = 33
               else: 
                   hilfe_id = 34
            else:
                hilfe_id = 35
                if erg > 0:
                    hilfe_id = 36
                else:
                    hilfe_id = 37
        elif typ in [7, 8, 9]:
            hilfe_id = 71
        else:
            hilfe_id = 74
        pro_text = text.replace(" ","")
        frage = pro_text + "="
        text = "Berechne:<br>" +text
        lsg = [str(erg).replace(".",",")] 
        return typ, typ2, titel, text, pro_text, frage, variable, einheit, anmerkung, lsg, hilfe_id, erg, {'name':'normal'}

def termteil(startbuchstabe, bis, stufe, positiv = False):
    buchstaben_liste = ["a","b","c","","x","y", "z", "", "u", "v","w",""]
    koeffizient = 0
    while koeffizient == 0:
        if stufe%2 == 1:
            if positiv:
                koeffizient = random.randint(1,3)
            else:
                koeffizient = random.randint(-4,5)
        else:
            if positiv:
                koeffizient = random.randint(1,3)                     
            else:
                koeffizient = random.randint(-2,5)                     
    naechster_buchstabe = random.randint(0,bis)
    index = startbuchstabe+naechster_buchstabe
    buchstabe = buchstaben_liste[index]
    term = "{}{}".format(koeffizient, buchstabe )
    if buchstabe != "":
        term = term.replace("1","")
    return term, koeffizient, buchstabe, naechster_buchstabe

def term_bereinigen(term, typ):
    rueckmeldung = ""
    nicht_erlaubt = []
    erlaubt = ['a','b','c','x','y','z','u','v','w','1', '2','3','4','5','6','7','8','9','0','+','-','*','^','²','³','(',')']
    if typ == 4:
        erlaubt = erlaubt[:25]
    elif typ == 2:
        erlaubt = erlaubt[:22]
    for e in erlaubt[:8]:
        if e+e in term:
            rueckmeldung = 'Anstelle von "{}" schreibt man "{}²".<br>'.format(e+e,e)
    for t in term:
        if t not in erlaubt:
            nicht_erlaubt.append("'"+t+"'")
    if len(nicht_erlaubt) == 1:
        falsch = ",".join(nicht_erlaubt)
        rueckmeldung += 'Das Zeichen {} gehört nicht in den Term!'.format(falsch)
    if len(nicht_erlaubt) > 1:
        falsch = " und ".join(nicht_erlaubt)
        rueckmeldung += ' Die Zeichen {} gehören nicht in den Term!'.format(falsch)    
        return ("", rueckmeldung)
    # if "1^2" in term or "1²" in term:
    #     return 0, "1² = 1!"
    term = term.replace("+", " +").replace("-"," -").replace("*","")
    teile = term.split(' ')
    n = 0
    for t in teile:
        if (re.search(r'[\d]²',t)):
            return 0, "{} musst du ausrechnen!".format(t)
        if not (re.search(r'1[\d]',t)) and (re.search(r'1[\D]',t)) and "1" in t:
            teile[n] = teile[n].replace("1","")
            t = t.replace("1","")
            rueckmeldung += '<br>Die "1" lässt man hier weg und schreibt nur "{}"<br>'.format(t)
        n +=1
    term = "".join(teile)
    if typ == 6:
        if "(" not in term:
            return 0, "Wo ist die Klammer?"
        teile = term.split("(")
        klammer = teile[1]                                          # selektiert die klammer
        klammer = klammer.replace("+", " +").replace("-"," -").replace(")","")
        klammer = klammer.strip()
        teile = klammer.split(' ')                                  # teilt den Klammerinhalt
        for e in erlaubt[:9]:
            if e in teile[0] and e in teile[1]:
                return 0,  '"{}" musst du auch noch ausklammern!'.format(e)
            else:
                teile[0] = teile[0].replace(e,"")
                teile[1] = teile[1].replace(e,"")
        for e in erlaubt[19:]:
            teile[0] = teile[0].replace(e,"")
            teile[1] = teile[1].replace(e,"")
        try:
            zahl1 = (int(teile[0]))
            zahl2 = (int(teile[1])) 
            if gcd(zahl1,zahl2) > 1:
                    return 0,  'Du musst noch den ggT aus {} und {} ausklammern!'.format(zahl1,zahl2)
        except:
            pass
    term = term.replace(" ","")
    if term[:1] == "+":
        term = term[1:]
    return(term, rueckmeldung)

def termwert(term):
    rueckmeldung = ""
    buchstaben_liste=['a', 'b', 'c', 'x', 'y', 'z', 'u', 'v', 'w']
    term = term.replace("*","").replace("(", "*(")
    term = term.replace("²", "^2")
    for b in buchstaben_liste:
        term = term.replace(b+b, b+"^2")
    for s in buchstaben_liste:
        term = term.replace("-"+s, "-1"+s)
        term = term.replace("+"+s, "+1"+s)
        term = term.replace(s,"*"+str(ord(s)))
    if term[:1] == "*":
        term = term[1:]
    term = term.replace("(*","(")
    parser = Parser()
    try:
        wert = parser.parse(term).evaluate({})
    except:
        rueckmeldung = "Den Term, den du eingegeben hast, kann ich nicht berechnen."
        wert = 0
    return(wert, rueckmeldung)

def sortieren(zahl,buchstaben):
    erlaubt = ['a','b','c','x','y','z','u','v','w']
    buchstaben.sort()
    buchstaben = "".join(buchstaben)
    for e in erlaubt:
        if e+e in buchstaben:
            buchstaben = buchstaben.replace(e+e,e+"²")
    term = "{:+d}{}".format(zahl,buchstaben)
    if abs(zahl) == 1 and buchstaben != "":
        term = term.replace("1","")
    return term

def terme(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "":                                                               
        typ_anf = 1
        typ_end = 3
        if "nur" in optionen:
            typ_anf = 7
            typ_end = 8
        elif stufe >= 23 or jg >= 9 or "binomisch" in optionen:
            typ_end = 8
        elif stufe >= 22 or jg >= 9 or "Klammern" in optionen:
            typ_end = 6
        return typ_anf, typ_end
    elif eingabe != "": 
        loe = (lsg[0])
        if typ in [2,3,4,5,6,7,8]:
            eingabe, rueckmeldung = (term_bereinigen(eingabe, typ))          # richtig wenn Eingabeterm bereinigt
            if eingabe == loe:
                return 1, rueckmeldung
            if rueckmeldung != "":
                return 0, rueckmeldung
            wert, rueckmeldung_wert = termwert(eingabe)
            if rueckmeldung_wert != "":                                      # Wert kann nicht berechnet werden
                return 0, rueckmeldung_wert
            if termwert(loe)[0] == wert:
                if typ == 7:
                    if  "(" in eingabe:
                        return 0, "Das stimmt so noch nicht" 
                    else:
                        return 1, ' - aber besser als "{}" gefällt mir "{}"'.format(eingabe,lsg[0]) 
                elif typ == 8:
                    if ")²" not in eingabe and eingabe.count("(")< 2:
                        return 0, "Das stimmt so noch nicht" 
                    else:
                        return 1, ' - aber besser als "{}" gefällt mir "{}"'.format(eingabe,lsg[0]) 
                elif typ in [4,5,6]:
                    if typ == 5 and typ2 == 2 and len(eingabe.replace("^2","²"))<=len(loe)+1:
                        return 2, "<br>Für das Zusammenfassen gibt es einen Extrapunkt!"
                    else: 
                        return 1, ' - aber besser als "{}" gefällt mir "{}"'.format(eingabe,lsg[0]) 
                else: 
                    if len(eingabe) <= len(loe)+1:
                        if rueckmeldung == "":
                            return 0, "Die Reihenfolge stimmt nicht - achte auf die Anmerkung!"
                        else:
                            return 0, rueckmeldung        
                    else:
                        return 0, "Den Term kann man weiter zusammenfassen."         
            else:
                return -1, rueckmeldung 
    else: 
        if aufgnr == 1 and typ_anf != 7:
            typ = 1 
        elif typ_anf == 7:
            typ = random.randint(typ_anf, typ_end) 
        else:
            typ = random.randint(2, typ_end) 
        typ2 = 0
        titel = "Terme" 
        text = "default{}"
        hilfe_text = frage = pro_text = anmerkung = einheit = lsg = ""
        variable = []
        hilfe_id = 0
        erg = None
        buchstaben_liste = ["a","b","c","","x","y", "z", "", "u", "v","w",""]
        lsg_koeff = [0,0,0,0,0,0,0,0,0,0,0,0]
        parameter = {'name':'normal'}
        if typ == 1:                                                                            # Wertetabelle'
            text = "Berechne jeweils den Wert des Termes"
            zahlen = [0,1,2,-1, 0.5]
            lsg = [""]
            absolut = koeffizient = 0
            while absolut == 0:
                absolut = random.randint(-4,4)
            while koeffizient == 0:
                if stufe%2 == 1:
                    koeffizient = random.randint(-4,4)
                else:
                    koeffizient = random.randint(1,5)
            term = "{}x {:+d}".format(str(koeffizient).replace("1",""), absolut)
            pro_text = "Termbelegung: " + term
            x_werte = {}
            y_werte = {}
            y_farbe = {}
            lsg = []
            for n in range (0,5):
                x_werte["x" + str(n)] = zahlen[n]
                y_werte["y" + str(n)] = zahlen[n]*koeffizient+absolut
                #y_farbe["color" + str(n)] = "leer"
                lsg.append(str(zahlen[n]*koeffizient+absolut))
            lsg = [lsg]
            parameter = {'name': 'tab_terme', 'titel_x': 'x', 'titel_y': term}
            parameter.update(x_werte)
            parameter.update(y_werte)
            parameter.update(y_farbe)
        elif typ == 2:                                                                          # Terme zusammenfassen
            items = stufe%2+4
            startbuchstabe = typ2 = random.randint(0,2)*4
            for n in range (items):
                term, koeffizient, buchstabe, naechster_buchstabe= termteil(startbuchstabe, 2, stufe)
                index = startbuchstabe+naechster_buchstabe
                lsg_koeff[index] +=koeffizient
                term = "{:+d}{}".format(koeffizient, buchstabe )
                if buchstabe != "":
                    term = term.replace("1","")
                frage += term
            if frage[:1] == "+":
                frage = frage[1:]
            n = 0
            for k in lsg_koeff:
                if k != 0:
                    buchstabe = buchstaben_liste[n]
                    t = "{:+d}{}".format(k, buchstabe )                   
                    if buchstabe != "" and abs(k) < 10:
                        t = t.replace("1","")
                    lsg += t
                n += 1
            if lsg[:1] == "+":
                lsg = lsg[1:]
            pro_text = frage+"="
            lsg = [lsg, "indiv_0"]                 
            text = "Vereinfache den Term so weit wie möglich:<br>" + frage
            anmerkung = "Du musst die Buchstaben nach dem Alphabet sortieren, Konstanten stehen am Ende"
            hilfe_id = 20
            variable = [buchstaben_liste[startbuchstabe],buchstaben_liste[startbuchstabe+naechster_buchstabe]]
            hilfe_text="Du musst alle Zahlen ohne Buchstaben zusammenfassen und dann jeweils alle {}'s und alle {}'s usw.! <br>"\
                "(Wenn vor einem Buchstaben keine Zahl steht, musst du dir eine 1 dazudenken.)<br> Achte auf die Vorzeichen!)<br>"\
                "Am Ende musst du alle Ausdrücke nach dem Alphabet sortieren.".format(*variable)
        elif typ == 3:                                              
            startbuchstabe = typ2 = random.randint(0,2)*4
            frage, koeffizient1, buchstabe1, leer = termteil(startbuchstabe, 2, stufe)
            frage2, koeffizient2, buchstabe2, leer = termteil(startbuchstabe, 2, stufe)
            if koeffizient2 < 0:
                frage +=" ·("+frage2+")"
            else:
                frage +=" ·"+frage2
            if koeffizient1*koeffizient2 == 1:
                koeffizient = ""
            else:
                koeffizient = koeffizient1*koeffizient2
            if buchstabe1 == buchstabe2:
                lsg = ["{}{}".format(koeffizient,(buchstabe1+"²")), "{}{}".format(koeffizient,(buchstabe1+"^2")), "indiv_0"]
                anmerkung = 'Buchstaben nach dem Alphabet sortieren.<br>(Du kannst anstelle von "²" auch "^2" eingeben)'
            else:
                variable = [buchstabe1,buchstabe2]
                variable.sort()
                lsg = ["{}{}".format(koeffizient,"".join(variable)),"indiv_0"]
                anmerkung = "Buchstaben nach dem Alphabet sortieren."
            hilfe_id = 30
            variable = [startbuchstabe]
            hilfe_text = 'Du musst einfach nur die Zahlen multiplizieren und die Buchstaben nach dem Alphabet sortieren! <br>'\
                '(Achte auf die Vorzeichen! Und beachte: "{0}·{0}" = "{0}²")'.format(startbuchstabe)
            pro_text = frage+"="
            text = "Multipliziere:<br>" + frage
        elif typ in [4,6]:                                                                      # 4 = Klammer auflösen, 6= ausklammern
            stufe=2
            startbuchstabe = typ2 = random.randint(0,2)*4
            if typ == 4:
                if stufe%2 == 1:
                    teil1, koeffizient1, buchstabe1, leer = termteil(startbuchstabe, 3, stufe)
                else:
                    buchstabe1 = "x"
                    koeffizient1 = 2
                    while (buchstabe1 != "" and koeffizient1 >1):               # entweder buchstabe oder koeffizient > 1 
                        teil1, koeffizient1, buchstabe1, leer = termteil(startbuchstabe, 3, stufe, True)
                if abs(koeffizient1) == 1 and buchstabe1 == "":
                    teil1 = "-"
                    if koeffizient1 == 1:
                        koeffizient1 = -1
            else:
                buchstabe1 = ""
                koeffizient = 1
                while buchstabe1 == "" and koeffizient == 1:
                    teil1, koeffizient1, buchstabe1, leer = termteil(startbuchstabe, 3, stufe)
                if stufe%2 != 1:                                                       # entweder buchstabe oder koeffizient > 1 
                    if buchstabe1 != "":
                        teil1 = buchstabe1
                        koeffizient1 = 1
                        typ2 = 2
            koeffizient2 = koeffizient3 = 2
            while gcd(koeffizient2, koeffizient3) > 1:                      # verhindert das Zahl nicht komplett ausgeklammert wurde
                teil2, koeffizient2, buchstabe2, leer = termteil(startbuchstabe, 3, stufe, True)
                buchstabe3 = buchstabe2
                while buchstabe2 == buchstabe3:
                    teil3, koeffizient3, buchstabe3, leer = termteil(startbuchstabe, 3, stufe)
            if koeffizient3 > 0:
                text = "{} ({} + {})".format(teil1,teil2,teil3)
            else:
                text = "{} ({} - {})".format(teil1,teil2,teil3.replace("-",""))
            if typ == 6:
                lsg = [text, "indiv_0"] 
                text = sortieren(koeffizient1*koeffizient2,[buchstabe1,buchstabe2])
                text += sortieren(koeffizient1*koeffizient3,[buchstabe1,buchstabe3])
                if text[:1] == "+":
                    text = text[1:]
                frage = pro_text = text
                text = "Klammere aus:<br>" + frage 
            else:            
                frage = pro_text = text.replace(" ", "")
                lsg = sortieren(koeffizient1*koeffizient2,[buchstabe1,buchstabe2])
                lsg += sortieren(koeffizient1*koeffizient3,[buchstabe1,buchstabe3])
                if lsg[:1] == "+":
                    lsg = lsg[1:]
                lsg = [lsg, lsg.replace("²","^2"),"indiv_0"]  
                text = "Löse die Klammer auf:<br>" + frage 
            if typ == 4:
                if "-(" in frage:
                    hilfe_id = 41 
                    hilfe_text = "hier handelt es sich um eine sogenannte Minusklammer - du musst nur einfach alle Vorzeichen in der Klammer umdrehen."
                else:
                    hilfe_id = 40 
                    variable = [buchstaben_liste[startbuchstabe]]
                    hilfe_text='Du musst den Ausdruck vor der Klammer zuerst mit dem ersten Ausdruck in der Klammer multiplizieren und dann mit dem zweiten! D.h.: Zahl mal Zahl und die Buchstaben nach dem Alphabet sortieren.'\
                        '<br>(Achte auf die Vorzeichen! Und beachte: {0}·{0} = {0}²)'.format(buchstaben_liste[startbuchstabe])
            else:
                if stufe%2 == 1:
                    hilfe_id = 61
                    hilfe_text = "Du musst den ggT der Zahlen und/oder einen Buchstaben finden, die in beiden Ausdrücken drinnen ist und diese vor die Klammer schreiben!"
                else:
                    if typ2 == 2:
                        hilfe_id = 62
                        hilfe_text = "Du musst den ggT der Zahlen finden und diese vor die Klammer schreiben!"
                    else:
                        hilfe_id = 63
                        hilfe_text = "Du musst einen Buchstaben finden, die in beiden Ausdrücken drinnen ist und diese vor die Klammer schreiben!"
        elif typ == 5:                                                                          # Klammer mal Klammer
            startbuchstabe = typ2 = random.randint(0,2)*4
            teil1 = buchstaben_liste[startbuchstabe+random.randint(0,3)]
            teil2 = teil1
            while teil2 == teil1:
                teil2 = buchstaben_liste[startbuchstabe+random.randint(0,3)]
            teil3 = buchstaben_liste[startbuchstabe+random.randint(0,3)]
            teil4 = teil3
            while teil4 == teil3:                           
                teil4 = buchstaben_liste[startbuchstabe+random.randint(0,3)]
            zusammenfassen = False
            if (teil1 == teil3 or teil1 == teil4) and (teil2 == teil3 or teil2 == teil4):
                zusammenfassen = True
                typ2 = 2
            vorz2 = random.choice(["+","+","-"])
            vorz4 = random.choice(["+","+","-"])
            if teil1 == "":
                teil1 = str(random.randint(1,5))
            if teil2 == "":
                teil2 = str(random.randint(1,5))
            if teil3 == "":
                teil3 = str(random.randint(1,5))
            if teil4 == "":
                teil4 = str(random.randint(1,5))
            text = "({}{}{}) ({}{}{})".format(teil1,vorz2,teil2,teil3,vorz4,teil4)
            if vorz2 == "-" and isinstance(teil2, int):
                teil2 = -1*teil2
            if vorz4 == "-" and isinstance(teil4, int):
                teil4 = -1*teil4
            frage = pro_text = text.replace(" ", "")
            lsg_term = [teil1+teil3,vorz4+teil1+teil4,vorz2+teil2+teil3,vorz2+teil2+vorz4+teil4]
            sort_term = []
            zahlen = ['1', '2','3','4','5','6','7','8','9'] 
            for teil_lsg in lsg_term:
                sortet = sorted(teil_lsg)
                teil_lsg = "".join(sortet)
                anzahl = zahl = 0
                for t in teil_lsg:                          # sucht Einträge aus Zahlen
                    if t in zahlen:
                        anzahl +=1
                if anzahl >1:                               # ersetzt zwei zahlen durch Produkt
                    zahl = int(teil_lsg[-1])*int(teil_lsg[-2])
                    teil_lsg = teil_lsg[:-2]+str(zahl)
                if anzahl == 1:
                    teil_lsg = teil_lsg.replace("1","")
                else:                                       # ersetzt durch ²
                    for e in ['a','b','c','x','y','z','u','v','w']:
                        if e+e in teil_lsg:
                            teil_lsg = teil_lsg[:-1]+"²"                   
                sort_term.append(teil_lsg)
            if sort_term[3][0] == sort_term[3][1]:          # gleiche Vorz = +, ungleiche -
                sort_term[3] = "+"+(sort_term[3])[2:]
            else:
                sort_term[3] = "-"+(sort_term[3])[2:]
            lsg = "".join(sort_term)
            lsg = [lsg, lsg.replace("²","^2"),"indiv_0"]  
            if zusammenfassen:
                buchstaben = ['a','b','c','x','y','z','u','v','w']
                sort_term[0] = "+"+ sort_term[0]
                zahl_stelle = quadrat_stelle = 0
                n = 1
                for s in sort_term:
                    try:
                        zahl = int(s)
                        zahl_stelle = n
                    except:
                        if "²" in s:
                            quadrat_stelle = n
                    n +=1 
                if zahl_stelle > 0:                                         # ist eine Zahl da, ist auch ein Quadrat da, die zahl kommt nach hinten
                    summe = 0
                    buchstabe = ""
                    if zahl_stelle in [1,4]:
                        for b in buchstaben:
                            if b in sort_term[1]:
                                sort_term[1] = sort_term[1].replace(b,"")
                                try:
                                    summe += int(sort_term[1])
                                except:
                                    if "+" in sort_term[1]:
                                        summe +=1
                                    else:
                                        summe -=1
                                sort_term[2] = sort_term[2].replace(b,"")
                                try:                                        # ergibt Fehler bei +x oder -x (weil die 1 fehlt)
                                    summe += int(sort_term[2])
                                except:
                                    if "+" in sort_term[2]:
                                        summe +=1
                                    else:
                                        summe -=1
                                buchstabe = b
                        mitte = "{:+d}{}".format(summe,buchstabe)
                    else:
                        for b in buchstaben:
                            if b in sort_term[1]:
                                sort_term[0] = sort_term[0].replace(b,"")
                                try:
                                    summe += int(sort_term[0])
                                except:
                                    if "+" in sort_term[0]:
                                        summe +=1
                                    else:
                                        summe -=1
                                sort_term[3] = sort_term[3].replace(b,"")
                                try:
                                    summe += int(sort_term[3])
                                except:
                                    if "+" in sort_term[3]:
                                        summe +=1
                                    else:
                                        summe -=1
                                buchstabe = b
                        mitte = "{:+d}{}".format(summe,buchstabe)
                    if abs(summe) == 1:
                        mitte = mitte.replace("1","")                       
                    if zahl_stelle == 1:
                        zusammen = sort_term[3]+mitte+sort_term[0]
                    elif zahl_stelle == 4:
                        zusammen = sort_term[0]+mitte+sort_term[3]
                    elif zahl_stelle == 2:
                        zusammen = sort_term[2]+mitte+sort_term[1]
                    else:
                        zusammen = sort_term[1]+mitte+sort_term[2]
                else:
                    if quadrat_stelle in [1,4]:
                        if sort_term[1] == sort_term[2]:
                            if "-" in sort_term[1]:
                                mitte = "-2"+sort_term[1].replace("+","")
                            else:
                                mitte = "+2"+sort_term[1].replace("+","")
                        else:
                            mitte = ""
                        if sort_term[0][1]>sort_term[3][1]:
                            zusammen = sort_term[3]+mitte+sort_term[0]
                        else:
                            zusammen = sort_term[0]+mitte+sort_term[3]
                    else:
                        if sort_term[0] == sort_term[3]:
                            if "-" in sort_term[1]:
                                mitte = "-2"+sort_term[0].replace("+","")
                            else:
                                mitte = "+2"+sort_term[0].replace("+","")
                        else:
                            mitte = ""
                        if sort_term[1][1]>sort_term[2][1]:
                            zusammen = sort_term[2]+mitte+sort_term[1]
                        else:
                            zusammen = sort_term[1]+mitte+sort_term[2]
                if zusammen[:1] == "+":
                    zusammen = zusammen[1:]
                lsg = [zusammen] + lsg
                anmerkung = "Wenn du den Term auch noch zusammenfasst, gibt es einen Extrapunkt!"
                hilfe_id = 51
                variable = [buchstaben_liste[startbuchstabe]]
                hilfe_text='Du musst jeden Ausdruck in der ersten Klammer mit jedem Ausdruck in der zweiten Klammer multiplizieren (Das ergibt vier Ausdrücke)'\
                    '<br>(Achte auf die Vorzeichen! Und beachte: {0}·{0} = {0}²)'\
                    '<br>Zuletzt sollst du noch die Teile, bei denen die Buchstaben übereinstimmen, zusammenfassen'.format(buchstaben_liste[startbuchstabe])
            else:
                hilfe_id = 50 
                variable = [buchstaben_liste[startbuchstabe]]
                hilfe_text='Du musst jeden Ausdruck in der ersten Klammer mit jedem Ausdruck in der zweiten Klammer multiplizieren (Das ergibt vier Ausdrücke)'\
                    '<br>(Achte auf die Vorzeichen! Und beachte: {0}·{0} = {0}²)'.format(buchstaben_liste[startbuchstabe])
            text = "Löse die Klammern auf:<br>" + frage 
        elif typ in[7,8]:                                                                       # binomische Formeln
            typ2 = random.randint(1,6)
            typ2=6
            startbuchstabe =  random.randint(0,2)*4
            buchstabe1 = buchstaben_liste[startbuchstabe+random.randint(0,3)]
            buchstabe2 = buchstabe1
            while buchstabe2 == buchstabe1:
                buchstabe2 = buchstaben_liste[startbuchstabe+random.randint(0,3)]
            zahl1 = random.randint(1,4)
            zahl2 = zahl1
            while gcd(zahl1,zahl2) > 1:
                zahl2 = random.randint(1,4)
            str_zahl1 = str(zahl1)
            str_zahl2 = "{:+d}".format(zahl2)
            buchstabe11 = buchstabe22 = ""                                                  # für die Lösungen
            if buchstabe1 != "":
                str_zahl1 = str_zahl1.replace("1","") 
            if buchstabe2 != "":
                str_zahl2 = str_zahl2.replace("1","") 
            if buchstabe1 != "":
                buchstabe11 = buchstabe1+"²"
            if buchstabe2 != "":
                buchstabe22 = buchstabe2+"²"
            str_zahl11 = str(zahl1*zahl1)
            if buchstabe1 != "" and zahl1*zahl1 < 10:
                str_zahl11 = str_zahl11.replace("1","")
            str_zahl22 = str(zahl2*zahl2)
            if buchstabe2 != "" and zahl2*zahl2 < 10:
                str_zahl22 = str_zahl22.replace("1","") 
            str_zahl12 = str(zahl1*zahl2*2)
            list_buchstaben12 = (buchstabe1+" "+buchstabe2).split()
            list_buchstaben12.sort()
            buchstaben12 = "".join(list_buchstaben12)
            if typ2 == 6:                                                                       # 3. bin. Formel                                                                        
                str_zahl3 = str_zahl2.replace("+","-")
                text = "({0}{1}{2}{3})({0}{1}{4}{3})".format(str_zahl1,buchstabe1,str_zahl2,buchstabe2,str_zahl3)
                lsg =  "{0}{1}-{2}{3}".format(str_zahl11,buchstabe11,str_zahl22,buchstabe22)
                if typ == 7:
                    hilfe_id = 73
                    hilfe_text = "Hier brauchst du die dritte binomische Formel: (a+b)(a-b)=a²-b²."
                else:
                    hilfe_id = 83
                    hilfe_text = "Hier brauchst du die dritte binomische Formel: a²-b² = (a+b)(a-b)."
            elif typ2 in [4,5]:
                str_zahl2 = str_zahl2.replace("+","-")
                if typ2 == 5:
                    text = "({0}{1}{2}{3})({0}{1}{2}{3})".format(str_zahl1,buchstabe1,str_zahl2,buchstabe2)
                else:
                    text = "({}{}{}{})²".format(str_zahl1,buchstabe1,str_zahl2,buchstabe2)
                lsg =  "{}{}-{}{}+{}{}".format(str_zahl11,buchstabe11,str_zahl12,buchstaben12,str_zahl22,buchstabe22)
                if typ == 7:
                    hilfe_id = 72
                else:
                    hilfe_id = 82
                    hilfe_text = "Hier brauchst du die zweite binomische Formel: (a-b)(a-b)=a²-2ab+b²"
            else:
                if typ2 == 3:
                    text = "({0}{1}{2}{3})({0}{1}{2}{3})".format(str_zahl1,buchstabe1,str_zahl2,buchstabe2)
                else:
                    text = "({}{}{}{})²".format(str_zahl1,buchstabe1,str_zahl2,buchstabe2)
                lsg =  "{}{}+{}{}+{}{}".format(str_zahl11,buchstabe11,str_zahl12,buchstaben12,str_zahl22,buchstabe22)
                if typ == 7:
                    hilfe_id = 71
                else:
                    hilfe_id = 81
                    hilfe_text = "Hier brauchst du die erste binomische Formel: (a+b)(a+b)=a²+2ab+b²"
            if typ == 7:
                frage = pro_text = text
                lsg = [lsg, "indiv_0"]
            else:
                pro_text = frage = lsg
                if typ2 == 6:
                    text1 = text.replace(")(",") (")
                    lsg1 = text1.split()
                    lsg = [text, lsg1[1]+lsg1[0],"indiv_0"]
                elif ")(" in text:
                    text1 = text.replace(")(",") (")
                    lsg1 = text1.split()
                    lsg = [lsg1[0]+"²",text,"indiv_0"]
                else:
                    lsg = [text, (text+text).replace("²",""),"indiv_0"]
                text = frage
            text = "Wende die binomischen Formeln an:<br>" + text
        return typ, typ2, titel, text, pro_text, frage+"=", variable, einheit, anmerkung, lsg, hilfe_id, erg, parameter

def gleichungen(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "":                                                               
        typ_anf = 1
        typ_end = 6
        return typ_anf, typ_end
    else:                                                                            
        if aufgnr < 6:
            typ = random.randint(typ_anf, 4) 
        else:
            typ = random.randint(typ_anf, typ_end+stufe%2)
        titel = "Gleichungen" 
        frage = "x="
        variable = ["",]
        pro_text = einheit = anmerkung =  ""
        erg = random.randint(1,9)
        absolut = 0
        while absolut == 0:
            absolut = random.randint(-4,4)
        koeff1 = random.randint(2,5)
        if typ == 1:
            pro_text = "{}x = {}"
            variable = [koeff1,koeff1*erg] 
            hilfe_id = 10
        elif typ == 2:
            pro_text = "x{:+d} = {}"
            variable = [absolut,absolut+erg]
            if absolut >1: 
                hilfe_id = 21
            else:
                hilfe_id = 22
        elif typ == 3:
            pro_text = "{}x{:+d} = {}"
            variable = [koeff1,absolut,koeff1*erg+absolut]
            if absolut >1: 
                hilfe_id = 31
            else:
                hilfe_id = 32
        elif typ == 4:
            pro_text = "{}{:+d}x = {}"
            variable = [absolut,koeff1,koeff1*erg+absolut]
            if absolut >1: 
                hilfe_id = 41
            else:
                hilfe_id = 42
        elif typ == 5:
            pro_text = "{} = {}x{:+d}"
            variable = [koeff1*erg+absolut,koeff1,absolut]
            if absolut >1: 
                hilfe_id = 51
            else:
                hilfe_id = 52
        elif typ == 6:
            koeff2 = koeff1
            while koeff2 == koeff1:
                koeff2 = random.randint(2,5) 
            zwischen = (koeff1-koeff2)*erg+absolut           
            pro_text = "{}x{:+d} = {}x{:+d}"
            variable = [koeff2,zwischen,koeff1,absolut]
            hilfe_id = 61
        elif typ == 7:
            koeff2 = koeff1
            while koeff2 == koeff1:
                koeff2 = random.randint(2,5) 
            zwischen = (koeff1*erg+absolut)*koeff2
            pro_text = "{}({}x{:+d}) = {}"
            variable = [koeff2,koeff1,absolut,zwischen,-1*absolut]
            if stufe%2 == 1:
                hilfe_id = 71
            else:
                if absolut > 0:
                    hilfe_id = 72
                else:
                    hilfe_id = 73
        text = "Löse folgende Gleichung <br>" + pro_text
        lsg = ["x="+str(erg)]                           
        return typ, 0, titel, text, pro_text, frage, variable, einheit, anmerkung, [lsg], hilfe_id, erg, {'name':'normal'}

def wahrscheinlichkeit(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "":                                                               
        typ_anf = 0
        typ_end = 12
        if stufe%2 == 1:
            typ_anf = -1
        if jg > 8 or stufe > 24 or "mit" in optionen:
            typ_end = 18
        return typ_anf, typ_end
    elif eingabe != "": 
        if typ > 7: 
            try:                                                                                         
                parser = Parser()
                eingabe = eingabe.replace(",",".")
                if (parser.evaluate(lsg[0],{})) == (parser.evaluate(eingabe,{})):
                    return 1, ""
                else:
                    return -1, ""
            except:
                return -1, ""
        elif typ == 0:
            if "{" in eingabe or "(" in eingabe:
                return 0, "Die Klammern steht schon da!"
            elif (",") not in eingabe:
                return 0, "Bitte die Werte mit Kommas trennen!"
            else:
                return -1, ""
        elif typ == -1:
            if eingabe.lower() == lsg[0]:
                return 1, ""
            else:
                return -1, ""
        else:
            return -1, ""
    else:                                                                            
        typ = random.randint(typ_anf, typ_end)
        typ=11
        typ2 = 0
        titel = "Wahrscheinlichkeitsrechnung"
        parameter = {'name':'normal'} 
        variable = ["",]
        pro_text = frage = einheit = anmerkung = hilfe = ""
        hilfe_id = 0
        erg = None 
        if typ == -1:                                   # Laplace
            text = "Handelt es sich bei Experiment:<br>"
            frage = "ja/nein"
            hilfe_id = -1
            hilfe = "Ein Laplace Experiment ist ein zufälliges Element, bei dem alle möglichen Ergebnisse gleich wahrscheinlich sind."
            typ2 = random.randint(1,7)
            if typ2 == 1: 
                experiment = "'Würfeln mit einem normalen Spielwürfel'"
                pro_text = "Würfel - Laplace?"
                lsg = ["ja","j"]
            elif typ2 == 2:
                experiment = "'Es wird mit zwei Würfeln gewürfelt, die Augenzahl wird addiert'"                
                pro_text = "Zwei Würfel - Laplace?"
                parameter = {'name': 'core/grafik.html', 'object': 'grafik/2wuerfel.jpg', 'breite': 300}
                lsg = ["nein","n"] 
            elif typ2 == 3:
                weiss = random.randint(5,10)
                schwarz = random.randint(5,10)
                variable = [weiss, schwarz]
                experiment = "'Ziehen einer Kugel aus einer Urne mit {} weißen und {} schwarzen Kugeln'"
                pro_text = "Urne - Laplace?"
                if weiss == schwarz:
                    lsg = ["ja","j"]
                else:
                    lsg = ["nein","n"] 
                farben = ['white','black']
                for m in range(weiss-1):
                    farben.append('white',)
                for m in range (schwarz-1):
                    farben.append('black',)

                random.shuffle(farben)
                kugeln = []
                for n in range(weiss+schwarz):
                    x = 215 + (n%5)*30 + n//5%2*5
                    y = 145 - n//5*29
                    farbe = farben[n]
                    kugel = (farbe,x,y)
                    kugeln.append(kugel)
                    n +=1
                parameter = {'name': 'svg/stochastik.svg', 'object': 'urne', 'center_x': 200, 'center_y':160, 'kugeln': kugeln}

            elif typ2 == 4:
                experiment = "'Ziehen einer Karte aus einem gewöhnlichen Set Spielkarten mit 52 Karten'"                
                pro_text = "Kartenspiel - Laplace?"
                lsg = ["ja","j"] 
            elif typ2 == 5:
                experiment = "'Werfen eines Würfels mit den Zahlen 1,3,5,7,9,11 versehen'"
                pro_text = "Würfel - Laplace?"
                lsg = ["ja","j"]                     
            elif typ2 == 6: 
                experiment = "'Zwei Würfel werden geworfen, der Würfel mit der höheren Augenzahl wird mit 10 multipliziert und die niedrigere Augenzahl dazu addiert'"
                anmerkung = "Beispielsweise liefert eine „2“ und eine „4“ das Spielresultat  42."           
                pro_text = "Zwei Würfel - Laplace?"
                parameter = {'name': 'core/grafik.html', 'object': 'grafik/maexchen.jpg', 'breite': 150}
                lsg = ["ja","j"] 
            else:
                typ3 = random.randint(1,3)
                if typ3 == 1:
                    farben = ["r","g","b","r","g","b"]
                    lsg = ["ja","j"] 
                elif typ3 == 2:    
                    farben = ["w","g","w","r","w","b"]
                    lsg = ["nein","n"] 
                else:
                    farben = ["g","r","r","b","g","b"]
                    lsg = ["ja","j"] 
                nenner = len(farben)
                color_dict = {'r': 'red', 'n': 'green', 'b': 'blue', 'g': 'yellow', 'w': 'white'}
                winkel = []
                n = 0
                for key in farben:
                    item = (n*(360/nenner),color_dict[key])
                    winkel.append(item)
                    n +=1
                experiment = "'Das unten gezeigte Glücksrad wird gedreht'" 
                pro_text = "Glücksrad: Laplace?"
                parameter = {'name': 'svg/stochastik.svg', 'object': 'n-eck'}
                center_x = 250 
                center_y = 110
                alfa = int(360/nenner)
                startwinkel = 90-alfa/2
                parameter.update({'n_eck': nenner, 'rotate': winkel,}) 
                koordinaten_dreieck = winkel_koordinaten(0, center_x, center_y, 30, alfa, startwinkel, None, "", 100)  
                parameter.update(koordinaten_dreieck)
            text += experiment + "<br>um ein Laplace Experiment?"
            lsg.append("indiv_0")                 
        elif typ == 0:                                  # Begriffe
            typ2 = random.randint(1,3)
            if typ2 < 3:
                frage = "Ω={{"
                text = "Gib den Ergebnisraum für folgenden Zufallsversuch an:<br>"
                pro_text = "Ergebnisraum: "
                hilfe_id = 1
                hilfe = "Die Menge aller möglichen Ergebnisse heißt Ergebnisraum.<br>Man bezeichnet ihn mit 'Ω' und setzt die einzelnen Ergebnisse in geschweifte Klammern."
            else:
                frage = "E={{"
                text = "Gib den Ereignisraum für folgenden Zufallsversuch an:<br>"
                pro_text = "Ereignisraum: "
                hilfe_id = 3
                hilfe = "Ein Ereignisraum ist die Menge der Ergebnisse eines Zufallsexperimentes, die die gewünschte Aussage erfüllen.<br>Man bezeichnet sie mit 'E' und setzt die einzelnen Ergebnisse in geschweifte Klammern.<br>"
            einheit = "}"
            #anmerkung = "(Trenne mehrere Ereigniss mit Kommas.)"
            if typ2 == 1:
                experiment = "'Ein Würfel wird geworfen'"
                menge = "1,2,3,4,5,6"
            elif typ2 == 2:
                experiment = "'Augenzahl bei zwei Würfeln'"
                menge = "2,3,4,5,6,7,8,9,10,11,12"
            elif typ2 == 3:
                experiment = "'Mit einem Würfel wird eine gerade Zahl gewürfelt'"
                menge = "2,4,6" 
            text += experiment
            pro_text += experiment
            lsg = [menge, menge.replace(",",";"),"indiv_0"]  
        elif typ == 1:                                  # Median
            titel = "Median"
            if stufe%2 == 1:
                tage = random.randint(5,6)
            else:
                tage = 5
            temperaturen = []
            for temperatur in range(tage):
                temperatur = random.randint(15,23)
                temperaturen.append(str(temperatur))  
            sortiert = temperaturen
            text = "Die Höchsttemperaturen in der ersten {1} Tagen im August betrugen: {2}° und {3}°<br>Gib den Median dieser Temperaturen an!"
            frage = "Median:"
            pro_text = "Median: {4}"
            einheit = "°"
            sortiert.sort()
            variable = [', '.join(sortiert),tage,"°, ".join(temperaturen[:-1]),temperaturen[-1],",".join(temperaturen)]
            if tage%2 == 1:
                erg = int(sortiert[2])
                lsg = [str(erg)+"°C"]
            else:
                erg = (int(sortiert[2])+int(sortiert[3]))/2
                lsg = [format_zahl(erg,1)+"°C"]
            hilfe_id = 10
            hilfe = "Du musst die Werte der Größe nach aufschreiben ({}), der mittlere Wert ist der Median.<br>Bei einer geraden Anzahl von Werten musst du den Mittelwert der mittleren beiden Zahlen bilden."
        elif typ == 2:                                  # Mittelwert
            titel = "Mittelwert"
            anzahl_note = [1,1,1]
            summe = 6
            for n in range(7):
                zufall = random.randint(0,2)
                anzahl_note[zufall] +=1
                summe +=zufall+1
            erg = summe/10
            lsg = [format_zahl(erg,1)]
            text="Der letzte Vokabeltest ist gut ausgefallen:<br>Es gab {1} mal eine Eins, {2} mal eine Zwei und {3} mal eine Drei<br>Berechne die Durchschnittsnote!"
            frage = "Durchschnittsnote:"
            pro_text = "Durchschnittsnote: {1}*1,{2}*2,{3}*3"
            hilfe_id = 20
            variable = ["Noten",anzahl_note[0],anzahl_note[1],anzahl_note[2]]
            hilfe = "Du musst alle {} zusammenzählen und durch die Anzahl der Arbeiten teilen."
        elif typ == 3:                                  # Mittelwert
            titel = "Mittelwert"
            hilfe_id = 20            
            if stufe%2 == 1:
                typ2 = random.randint(1,2)
            else:
                typ2 = 2 
            if typ2 == 1:  
                temperaturen = []
                summe = 0
                for temperatur in range(10):
                    temperatur = random.randint(-2,6)
                    temperaturen.append(str(temperatur)) 
                    summe += temperatur 
                erg = summe/10
                lsg = [format_zahl(erg,1)+"°"]                             
                text = "Die Tiefsttemperaturen an den ersten zehn Tagen im Januar betrugen:<br>{1}° und {2}°<br>Berechne die durchschnittliche Tiefsttemperatur!"
                frage = "Durchschnittstemperatur:"
                pro_text = " Durchschnittstemperatur: {3}"
                einheit = "°"
                variable = ["Temperaturen","°, ".join(temperaturen[:-1]),temperaturen[-1],temperaturen]
                hilfe_id = 31
            else:
                noten = []
                summe = 0
                for note in range(10):
                    note = random.randint(1,4)
                    noten.append(str(note)) 
                    summe += note
                erg = summe/10
                lsg = [format_zahl(erg,1)]                             
                name = ["Tom", "Ali", "Lisa", "Marie"]
                text = "{} hat im Zeugnis folgende Noten:<br>{} und eine {}<br>Berechne die Durchschnittsnote!"
                pro_text = "Durchschnittsnote: {3}"
                frage = "Durchschnittsnote  "
                variable = [name[random.randint(0,3)],", ".join(noten[:-1]),noten[-1],noten]
                hilfe_id = 32
        elif typ == 4:                                  # Zahlenschloss
            titel = "Permutationen"
            anzahl = random.randint(3,4)
            if anzahl == 3:
                    parameter = {'name': 'core/grafik.html', 'object': 'grafik/schloss3.jpg', 'breite': 300}
            else:
                    parameter = {'name': 'core/grafik.html', 'object': 'grafik/schloss4.jpg', 'breite': 300}
            text = "Ein Zahlenschloss für das Fahrrad hat {0} Ziffern<br>Wie viele Einstellmöglichkeiten gibt es, wenn man diejenigen mit {0} gleichen Ziffern nicht mitzählt?".format(anzahl)
            pro_text = "Möglichkeiten Zahlenschloss {} Möglichkeiten"
            frage = "Es sind"
            einheit = "Möglichkeiten"
            pro_text = "Permutationen {0} Zahlen - 10".format(anzahl)
            erg=10**anzahl-10
            lsg = [str(erg)]
        elif typ == 5:                                  # Permutationen Buchstaben Ziffern
            titel="Kombinationen"
            typ2 = random.randint(1,2)
            if typ2 == 1:
                typ3 = "Buchstaben"
                werte = ["'R','O' und 'T'", "'B','L','A' und 'U'", "'G','E','L' und 'B'","'G','R','Ü' und 'N'","'B','R','A','U' und 'N'"]
            else:
                typ3 = "Zahlen"
                werte = ["1, 2 und 3", "1, 2, 3 und 4", "2, 4, 6 und 8","1, 3, 5, und 7","1, 2, 3, 4 und 5"]
            if stufe%2 == 1:
                zufall = random.randint(0,4)
            else:
                zufall = random.randint(0,3)
            anzahl = [3,4,4,5,5]
            ergebnis = [6,24,24,24,120]
            variable = [typ3, werte[zufall], anzahl[zufall]]
            text="Wie viele Möglichkeiten gibt es, die {}<br>{}<br>zu kombinieren?"
            pro_text = "Permutationen: {2} {0}"
            frage = "Es sind"
            einheit = "Möglichkeiten"
            erg = ergebnis[zufall]
            lsg = [str(erg)]
            hilfe_id = 50
            hilfe ="Für den ersten Buchstaben gibt es {2} Möglichkeiten, für den zweiten gibt es {2}-1 Möglichkeiten usw.. Dann muss man die Möglichkeiten multiplizieren." 
        elif typ == 6:                                  # Händeschütteln
            titel="Kombinationen"
            zufall = random.randint(3,5)
            variable = [zufall]	
            text = "{} Personen begegnen sich. Jeder schüttelt jedem die Hand.<br>Wie oft werden Hände geschüttelt"
            pro_text = "Händeschütteln {} Personen"
            if zufall == 3:
                parameter = {'name': 'core/grafik.html', 'object': 'grafik/haende3.jpg', 'breite': 300}
            elif zufall == 4:
                parameter = {'name': 'core/grafik.html', 'object': 'grafik/haende4.jpg', 'breite': 300}
            else:
                parameter = {'name': 'core/grafik.html', 'object': 'grafik/haende5.jpg', 'breite': 300}
            einheit = "Mal"
            erg = 0
            for n in range(zufall):
                erg += n
            lsg = [str(erg)]
            hilfe_id = 60
            hilfe = "Man kann das natürlich ausprobieren. Man kann es aber auch berechnen:<br>Die erste Person schüttelt {0}-1 Hände, die zweite nur noch {0}-2 usw..<br>Dann muss man die Möglichkeiten addieren." 			
        elif typ in (7,8):                              # 7=absolute Häufigkeit, 8=relative
            if typ == 7:
                art = "absolute"
                titel = "Absolute Häufigkeit"
            else:
                art = "relative"
                titel="Relative Häufigkeit"
            typ2 = random.randint(1,2)
            ereignisse = []
            if typ2 == 1: 
                name = ["Tom", "Ali", "Lisa", "Marie"]
                zufall1 = random.randint(0,3)
                zufall2 = zufall1
                while zufall2 == zufall1:
                    zufall2 = random.randint(0,3)   
                for n in range(20):
                    wurf = random.randint(1,6)
                    ereignisse.append(str(wurf))
                gesucht = str(random.randint(1,6))
                variable = [", ".join(ereignisse),art,gesucht,"Würfe","Zahl", name[zufall1],name[zufall2]]
                text= "Um herauszubekommen, ob die Zahlen beim Würfeln gleich häufig kommen, legen {5} und {6} eine Strichliste an:<br>{0}<br>Gib die <b>{1}</b> Häufigkeit für '{2}' an!" 
                pro_text = "{1} Häufigkeit: Würfel"
            else:
                farben = ["w","s","m","b","r","g","a"]
                farbname = ["weiss","schwarz","metallicsilber","blau","rot","gelb","andere"]
                zufall = random.randint(0,6)
                gesucht = farben[zufall]
                for n in range(20):
                    farbe = farben[random.randint(0,6)]
                    ereignisse.append(farbe)
                gesucht = farben[zufall]
                variable = [", ".join(ereignisse),art,farbname[zufall],"Autos","Farbe"]
                text = "Um herauszubekommen, welche Autofarben am häufigsten sind, wurden fünf Minuten lang die Farben der vorbeifahrenden Autos notiert:<br>{0}<br>Gib die <b>{1}</b> Häufigkeit der Autos mit der Farbe '{2}' an!"
                pro_text = "{1} Häufigkeit: Autofarben"
                anmerkung="(w) weiß, (s) schwarz, (m) silbermetallic, (b) blau, (r) rot, (g) gelb, (a) andere"
            frage = "Die {1} Häufigkeit für '{2}' beträgt"
            erg = ereignisse.count(gesucht)
            if typ == 7:
                lsg = [str(erg)]
                hilfe_id = 70
                hilfe = "Für die absolute Häufigkeit, muss man nur die Anzahl der {3} mit der entsprechenden {4} angeben."
            else:
                bruch = Fraction(erg/20).limit_denominator()
                lsg = [str(erg)+"/20",str(erg/20).replace(".",",")]
                erg = None
                hilfe_id = 80
                hilfe = "Für die relative Häufigkeit, muss man die Anzahl der {3} mit der entsprechenden {4} durch die Anzahl der {3} teilen."
        elif typ == 9:                                  # Glücksrad
            nenner = 11
            while nenner in (7,9,11):
                nenner = random.randint(6,12)
            farben_dict = {'r': 'rot', 'n': 'grün', 'b': 'blau', 'g': 'gelb'}
            color_dict = {'r': 'red', 'n': 'green', 'b': 'blue', 'g': 'yellow'}
            farben = []
            for farbe in range(nenner):
                farbe = random.choice(list(farben_dict))
                farben.append(farbe)
            gesucht = ""
            while gesucht not in farben:    
                gesucht = random.choice(list(farben_dict))
            zaehler = farben.count(gesucht)
            #bruch = Fraction(zaehler/nenner).limit_denominator()
            lsg = [str(zaehler)+"/"+str(nenner),str(zaehler/nenner).replace(".",",")]
            winkel = []
            n = 0
            for key in farben:
                item = (n*(360/nenner),color_dict[key])
                winkel.append(item)
                n +=1
            variable = [farben_dict[gesucht], nenner, zaehler]
            text =" Wie groß ist die Wahrscheinlichkeit dass beim Drehen des Glücksrades die Farbe '{}' kommt? " 
            pro_text = "Glücksrad mit {} Segmenten {}{}"
            parameter = {'name': 'svg/stochastik.svg', 'object': 'n-eck'}
            hilfe_id = 90
            hilfe = "Für die relative Häufigkeit, muss man die Anzahl der {}en Segmente durch die Gesamtzahl der Segmente teilen.<br>(Das kann man am einfachsten als Bruch angeben.)"
            center_x = 250 
            center_y = 110
            alfa = int(360/nenner)
            startwinkel = 90-alfa/2
            parameter.update({'n_eck': nenner, 'rotate': winkel,}) 
            koordinaten_dreieck = winkel_koordinaten(0, center_x, center_y, 30, alfa, startwinkel, None, "", 100)  
            parameter.update(koordinaten_dreieck)
        elif typ == 10:                                 # Urne
            farben_liste = ['white','red','yellow','blue','white','white','white','red','red','yellow',]
            color_dict = {'white':'weiß','red': 'rot', 'yellow': 'gelb', 'blue': 'blau'}
            nenner = random.randint(10,20)
            farben = []
            kugeln = []
            variable = []
            n = weiss = rot = blau = gelb = 0
            for kugel in range(nenner):
                x = 215 + (n%5)*30 + n//5%2*5
                y = 145 - n//5*29
                farbe = farben_liste[random.randint(0,9)]
                farben.append(farbe)
                kugel = (farbe,x,y)
                kugeln.append(kugel)
                n +=1
            weiss = farben.count("white")
            if weiss > 0:
                variable.append(weiss,)
                variable.append("weiß",)
            rot = farben.count("red")
            if rot > 0:
                variable.append(rot,)
                variable.append("rot",)
            blau = farben.count("blue")
            if blau > 0:
                variable.append(blau,)
                variable.append("blau",)
            gelb = farben.count("yellow")
            if gelb > 0:
                variable.append(gelb,)
                variable.append("gelb",)
            dubletten = set(farben)
            anzahl = len(dubletten)
            gesucht = ""
            while gesucht not in farben:
                gesucht = farben_liste[random.randint(0,3)]
            parameter = {'name': 'svg/stochastik.svg', 'object': 'urne', 'center_x': 200, 'center_y':160, 'kugeln': kugeln}
            variable.append(color_dict[gesucht])            
            text="In einer Urne befinden sich {} {}e"
            if anzahl >2:
                text += ", {} {}e" 
            if anzahl >3:
                text += ", {} {}e" 
            text += " und {} {}e Kugeln.<br>Wie groß ist die Wahrscheinlichkeit eine {}e Kugel zu ziehen?" 
            zaehler = farben.count(gesucht)
            pro_text = "Urne mit " + str(zaehler) + gesucht + "e von " +str(nenner) + " Kugeln"
            lsg = [str(zaehler)+"/"+str(nenner),str(zaehler/nenner).replace(".",",")]
            hilfe_id = 100
            hilfe = "Für die relative Häufigkeit, muss man die Anzahl der Kugeln der gesuchten Farbe durch die Gesamtzahl der Kugeln teilen.<br>(Das kann man am einfachsten als Bruch angeben.)"
        elif typ == 11:                                 # Würfeln und Münze
            parameter = {'name': 'core/grafik.html', 'object': 'grafik/wuerfel.jpg', 'breite': 300}
            typ2 = random.randint(1,4)
            typ2=1
            if typ2 == 1:
                zufall = random.randint(2, 7)
                text="Wie groß ist die Wahrscheinlichkeit beim Würfeln mit einem Würfel eine kleinere Zahl als {} zu würfeln?".format(zufall)  
                frage = "P(<{})=".format(zufall)
                zaehler = zufall-1
                lsg=[str(zaehler)+"/6"]	
            elif typ2 == 2:
                zufall = random.choice(["gerade","ungerade"])
                text="Wie groß ist die Wahrscheinlichkeit beim Würfeln mit einem Würfel eine {} Zahl zu würfeln?".format(zufall) 
                frage = "P({})=".format(zufall)
                lsg=["3/6","1/2"]
            elif typ2 ==3:
                text="Wie groß ist die Wahrscheinlichkeit beim Würfeln mit einem Würfel eine '{}' zu würfeln?" 
                frage= "P({})=" 
                lsg=["1/6"]
            else:
                parameter['object'] = 'grafik/muenzwurf.jpg'
                parameter['breite'] = 200
                variable = [random.choice(["Zahl", "Kopf"])] 
                text="Wie groß ist die Wahrscheinlichkeit beim Münzwurf '{}' zu würfeln?"
                anmerkung = "Dass die Münze auf dem Rand stehen bleiben kann, vernachlässigen wir." 
                frage= "P({})=" 
                lsg=["1/2"]
            if typ2 < 3:
                pro_text = "Würfel: " + frage.format(*variable)
            else:
                pro_text = "Münzwurf: " + frage.format(*variable)
            hilfe_id = 110
            hilfe="Du musst die Anzahl der erwünschten Ereignisse durch die Anzahl aller Möglichkeiten teilen.<br>(Gib das Ergebnis einfach als Bruch an)"
        elif typ == 12:                                 # Karten
            typ2 = random.randint(1,2)
            parameter = {'name': 'core/grafik.html', 'object': 'grafik/skat.png', 'breite': 300}
            werte = ("Sieben", "Acht", "Neun", "Zehn", "Bube", "Dame", "König", "Ass", "Zahl", "Bild")
            farben = ("Karo", "Herz", "Pik", "Kreuz", "rote", "schwarze")
            endungen1 = ("e","e","e","e","en","e","en","","e","")
            endungen2 = ("","","","","n","","n","s","","s") 			 
            wert = random.randint(0,9)
            farbe = random.randint(0,5)
            endung2 = endungen2[wert] if farbe > 3 else ""
            endung3 = "n" if wert == 4 else ""
            variable = [farben[farbe], werte[wert], endungen1[wert],endung2,endung3]
            text = "Ein Kartenspiel besteht aus 32 Karten:<br>Den Zahlen (7, 8, 9, 10) den Bildern (Bube, Dame, König) und dem Ass. Alle Karten  gibt es viermal: Karo, Herz, Pik und Kreuz.<br>Eine Karte wird gezogen.<br>Wie groß ist die Wahrscheinlichkeit ein" 
            frage = "P({0}{3} {1})="
            pro_text = "Kartenspiel:" + frage.format(*variable)
            typ2=1
            if typ2 == 1:
                text += "{2} {0}{3} {1}{4} zu ziehen?"		 		
            else:
                text += "{2} {0} {1} {4} zu ziehen?"	
            zaehler = 2 if farbe >3 else 1

            if wert == 8:
                zaehler *= 4
            elif wert == 9:
                zaehler *= 3
            nenner=32
            lsg = [str(zaehler)+ "/32"]
            hilfe_id = 120
            hilfe="Du musst die Anzahl der erwünschten Ereignisse durch die Anzahl aller Möglichkeiten teilen."
        # 2-stufige Versuche mit Zurücklegen
        elif typ == 13:                                 # Münzen
            parameter['object'] = 'grafik/muenzwurf.jpg'
            anzahl_dict = {2: "zweimal", 3: "dreimal"}
            anzahl = random.randint(2,3)
            parameter['breite'] = 200
            zufall_dict = {'K': 'Kopf', 'Z': 'Zahl'}
            zufall = random.choice(["Z", "K"]) 
            variable = [zufall, anzahl_dict[anzahl], zufall_dict[zufall]]
            anmerkung = "Dass die Münze auf dem Rand stehen bleiben kann, vernachlässigen wir." 
            if anzahl == 2:
                frage= "P({0};{0})="
                pro_text = "P: 2*gleicher Münzwurf"
            else:
                frage= "P({0};{0};{0})="
                pro_text = "P: 3*gleicher Münzwurf"                 
            nenner = 2**anzahl 
            lsg=["1/"+str(nenner)]   
            text="Eine Münze wird {1} geworfen. Wie groß ist die Wahrscheinlichkeit zweimal '{2}' zu werfen?"
            pro_text = "Münzwurf" + str(anzahl) + " Würfe" 
            hilfe_id = 130
            hilfe="Das ist ein zweistufiges Experiment. Du musst die Wahrscheinlichkeiten vom ersten und zweiten ... Ereignis multiplizieren<br>(Gib das Ergebnis am Besten als Bruch an)."
        elif typ == 14:                                 # Würfel
            zufall = random.randint(1,6)
            variable = [zufall]
            text="Wie groß ist die Wahrscheinlichkeit mit einem Würfel zweimal eine '{}' zu würfeln?"
            pro_text = "P: 2*gleiche Zahl würfeln" 
            frage= "P({0};{0})="
            lsg=["1/36"]
            hilfe_id = 140
            hilfe = "Das ist ein zweistufiges Experiment. Du musst die Wahrscheinlichkeiten vom ersten und zweiten Wurf multiplizieren (Am Besten als Bruch)."	
        elif typ == 15:                                 # Pasch
            text="Wie groß ist die Wahrscheinlichkeit mit zwei Würfeln einen Pasch zu würfeln?" 
            parameter = {'name': 'core/grafik.html', 'object': 'grafik/2wuerfel.jpg', 'breite': 300}
            pro_text = frage = "P(Pasch)="
            anmerkung = "(Pasch = zweimal die gleiche Augenzahl)"
            lsg=["6/36"]
            hilfe_id = 150
            hilfe = "Am einfachsten überlegst du, wieviele Möglichkeiten es insgesamt gibt und wieviele davon ein Pasch darstellen (Am Besten als Bruch)."	
        elif typ == 16:                                 # Kirschen
            zufall = random.randint(1,4)*10
            variable = [zufall]
            text = "Die Wahrscheinlichkeit, dass in einer Kirsche in diesem  Korb ein Wurm ist, beträgt {}%. Wie groß ist die Wahrscheinlichkeit, dass zwei Kirschen, die du aus dem Korb nimmst, verwurmt sind?" 
            parameter = {'name': 'core/grafik.html', 'object': 'grafik/kirschen.jpg', 'breite': 200}
            pro_text = frage = "P(2 Kirschen mit Würmern)="		 
            lsg = [str(int(zufall*zufall/100))+"/100"]
            hilfe_id = 160
            hilfe = "Das ist ein zweistufiges Experiment. Du musst die Wahrscheinlichkeit mit sich selbst multiplizieren.<br>Dazu musst du den Prozentwert zunächst in den entsprechenden Bruch oder eine Kommazahl umwandeln."	
        elif typ == 17:                                 # Socken
            weiss = random.randint(2,5)  
            schwarz = random.randint(2,5)
            farbe = ["weiß", "schwarz"]
            anzahl = [weiss, schwarz]
            zufall = random.randint(0,1)
            gesucht = farbe[zufall]    
            variable = [weiss, schwarz, gesucht]
            text="In der Sockenschublade liegen {0} weiße Socken und {1} schwarze Socken.<br>Wie groß ist die Wahrscheinlichkeit im Dunkeln ein Paar {2}e Socken herauszuziehen?"
            frage = "P({2},{2})="
            pro_text = "Socken: " + frage.format(*variable)
            zaehler = anzahl[zufall]*(anzahl[zufall]-1)
            nenner = (weiss+schwarz)*((weiss+schwarz)-1)	 
            lsg = [str(zaehler)+"/"+str(nenner)]
            hilfe_id = 170
            hilfe ="Das ist ein zweistufiges Experiment ohne Zurücklegen.<br>Beim ersten Socken hat man {} Möglichkeiten, beim zweiten Socken nur noch {}.<br>Du musst die beiden Wahrscheinlichkeiten multiplizieren. Am besten als Bruch!"
        elif typ == 18:                                 # Urne 2 Kugeln
            farben = ['blue','red','white']
            color_dict = {'white':'weiß','red': 'rot', 'blue': 'blau'}
            rot = random.randint(2,4)
            weiss = (9-rot)
            for m in range(rot-1):
                farben.append('red',)
            for m in range (weiss-1):
                farben.append('white',)
            zufall = random.randint(1,2)
            if zufall == 1:
                zaehler = rot*(rot-1)
            else:
                zaehler = (weiss)*(weiss-1)
            gesucht = farben[zufall]
            variable = [rot, weiss, color_dict[gesucht]]  
            random.shuffle(farben)
            kugeln = []
            for n in range(10):
                x = 215 + (n%5)*30 + n//5*5
                y = 145 - n//5*29
                farbe = farben[n]
                kugel = (farbe,x,y)
                kugeln.append(kugel)
                n +=1
            parameter = {'name': 'svg/stochastik.svg', 'object': 'urne', 'center_x': 200, 'center_y':160, 'kugeln': kugeln}
            text="In einer Urne befinden sich eine blaue, {0} rote und {1} weiße Kugeln.<br>Wie groß ist die Wahrscheinlichkeit zwei {2}e Kugeln zu ziehen?" 
            pro_text = "Urne mit {0} und {1} Kugeln"
            anmerkung = "(Ohne Zurücklegen)"
            lsg = [str(zaehler)+"/90"] 
            hilfe_id = 180
            hilfe ="Das ist ein zweistufiges Experiment ohne Zurücklegen.<br>Bei der ersten Kugel hat man ? Möglichkeiten, bei der zweiten Kugel eine weniger.<br>Du musst die beiden Wahrscheinlichkeiten multiplizieren. Am besten als Bruch!"
        if typ > 7:
            parser = Parser()
            zahl = (parser.evaluate(lsg[0],{}))
            if (zahl*10)%1==0:
                lsg.append(format_zahl(zahl,1))
            if (zahl*100)%1==0:
                lsg.append(format_zahl(zahl,2))
                lsg.append(format_zahl(zahl*100,0)+"%")                        
            lsg.append("indiv_0")
        return typ, typ2, titel, text, pro_text, frage, variable, einheit, anmerkung, lsg, hilfe_id, erg, parameter

def funktionen(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    if optionen != "":                                                               
        typ_anf = 1
        typ_end = 1

        return typ_anf, typ_end
    else:  
        # if aufgnr == 1 and typ_end < 8:
        #     typ = 1 
        # elif typ_anf == 7:
        #     typ = random.randint(typ_anf, typ_end) 
        # else:
        #     typ = random.randint(2, typ_end) 
        typ=1
        typ2 = 0
        titel = "Funktionen" 
        text = "default{}"
        hilfe_text = frage = pro_text = anmerkung = einheit = lsg = ""
        variable = []
        hilfe_id = 0
        erg = None
        parameter = {'name':'normal'}
        if typ == 1: 
            print("OK")                                                                           # Wertetabelle'
            text = "Berechne die Funktionswerte"
            zahlen = [0,1,2,-1]
            lsg = [""]
            absolut = koeffizient = 0
            while absolut == 0:
                absolut = random.randint(-4,4)
            while koeffizient == 0:
                if stufe%2 == 1:
                    koeffizient = random.randint(-4,4)
                else:
                    koeffizient = random.randint(1,5)
            term = "{}x {:+d}".format(str(koeffizient).replace("1",""), absolut)
            pro_text = "Termbelegung: " + term
            x_werte = {}
            y_werte = {}
            y_farbe = {}
            lsg = []
            for n in range (0,4):
                x_werte["x" + str(n)] = zahlen[n]
                y_werte["y" + str(n)] = zahlen[n]*koeffizient+absolut
                #y_farbe["color" + str(n)] = "leer"
                lsg.append(str(zahlen[n]*koeffizient+absolut))
            lsg = [lsg]
            parameter = {'name': 'tab_term', 'titel_x': 'x', 'titel_y': "y = " + term}
            parameter.update(x_werte)
            parameter.update(y_werte)
            parameter.update(y_farbe)
        return typ, typ2, titel, text, pro_text, frage+"=", variable, einheit, anmerkung, lsg, hilfe_id, erg, parameter

#"default" zum Erstellen neuer Aufgaben-Kategorien <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
def default(jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    #hier wird typ_anf und typ_end festgelegt. Das heißt von welchem Aufgabentyp ("typ") die 10 Aufgaben gemacht werden müssen (genauer: aufgerufen werden). 
    #Das kann u.u. noch unter 'Optionen' ausgeweitet werden (z.B. mit Komma oder ohne)
    if stufe%1>1:               # hiermit können Aufgaben nur für den A-Kurs erstellt werden
        typ_end = 20
    if optionen != "":                                                               
        typ_anf = 1
        typ_end = 1
        if stufe >= 6 or jg >= 7 or "mit" in optionen:
            typ_end = 2
        return typ_anf, typ_end
    #wenn in Lösungen 'indiv' steht und die eingegebene Lösung in "kontrolle" nicht als richtig bewertet wurde, kann die Lösung hier überprüft werden 
    elif eingabe != "":                                                                                                         
        loe = (lsg[0])
        if eingabe.replace(" ","") != loe.replace(" ",""):
            erg = loe.replace(",",".")
            eing = eingabe.replace(",",".")
            if float(erg) == float(eing):
                return 0, "Du darfst die Null am Ende nicht weglassen - <br>Die Zahl muss genau {0} Stellen hinter dem Komma haben".format(len(erg)-erg.find("."))
        else:
            return 0, "" 
    #hier wird letztendlich die Aufgabe erstellt:
    else:                                                                            
        typ = random.randint(typ_anf, typ_end)  
        typ2 = 0
        titel = "Titel" 
        text = "default{}"
        variable = ["",]
        pro_text = frage = einheit = anmerkung = hilfe = ""
        hilfe_id = 0
        erg = None 
        if typ == 1:
                zahl1 = random.randint(0,2)
                text = ""
                variable = [str(zahl1)]
                erg = None
                lsg = str(erg)
        else:
            pass
        lsg = [lsg] + ["indiv_0"]                                                         #sorgt dafür, dass die Eingabe nochmals in der Funktion der Aufgabe überprüft wird                             
        hilfe = hilfe.format(*variable)
        return typ, typ2, titel, text, pro_text, frage, variable, einheit, anmerkung, [lsg], hilfe_id, erg, {'name':'normal'}

def get_user(user):
    return Profil.objects.get(user = user)
    #return Profil.objects.all().first()

# dies war die Startseite
def kategorien(req):
    if req.user.is_authenticated: 
        if not User.objects.filter(pk=req.user.id, groups__name='Schüler').exists():
            return redirect('lehrer')
    Protokoll.objects.filter(eingabe = "").delete()
    kategorie = Kategorie.objects.all().order_by('zeile')
    return render(req, 'core/kategorien.html', {'kategorie': kategorie})

def durchschnitt_aufgaben(user):
    protokoll = Protokoll.objects.filter(user=user, sj=user.sj, hj=user.hj)
    zaehler = Zaehler.objects.filter(user=user)
    queryset = zaehler.order_by("letzte").last()
    letzte = queryset.letzte.strftime("%d.%m.%y %H:%M")
    temp = protokoll.aggregate(Sum('richtig'))['richtig__sum']
    richtig_gesamt = temp if temp else  0
    falsch_gesamt = zaehler.aggregate(sum=Sum('fehler_zaehler'))['sum']
    abbr_gesamt = zaehler.aggregate(sum=Sum('abbr_zaehler'))['sum']
    lsg_gesamt = zaehler.aggregate(sum=Sum('lsg_zaehler'))['sum']
    hilfe_gesamt = zaehler.aggregate(sum=Sum('hilfe_zaehler'))['sum']
    anzahl = zaehler.filter(sj = user.sj, hj = user.hj).count()                             # Anzahl der, in diesem Hj bearbeiteten Kategorien                                                       
    if anzahl == 0:
        durchschnitt = 0
    else:
        durchschnitt = int(richtig_gesamt/anzahl)
    return durchschnitt, richtig_gesamt, falsch_gesamt, abbr_gesamt, lsg_gesamt, hilfe_gesamt

def soll_berechnung(sj, hj, jg, aufgaben_pro_woche, startdatum):
    d0 = date(sj//100+2000,7,24)
    d1 = date.today()
    delta = d1 - d0
    aufg1hj = [1,1,1,1,2,3,4,5,6,7,8,8,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23]           # weniger Aufgaben am Anfang und keine in den Ferien - maximal 1600 (siehe unten)
    aufg2hj = [1,1,2,3,4,5,6,7,8,9,10,10,10,11,12,13,14,15,16,17,18,19,20,21,22,23, 24,25, 26]   
    schulwoche = delta.days//7                                                                  # Schulwoche wird benötigt um Anzuzeigen welche Kategorien bearbeitet werden müssen
    if schulwoche < 0: 
        #print("kleiner")                                                                       # wenn Aufgaben schon im Halbjahr vorher begonnen wurden
        schulwoche = 0  
    if hj == 2:
        zweites_hj = (sj%100+2000)
        d2 = date(zweites_hj,1,24)
        delta2 = d1 - d2
        woche_halbjahr =  delta2.days//7                                                        # wird benötigt um auszurechnen, wieviele Aufgaben gerechnet werden sollten
        try:
            spaeter = ((startdatum.date()-d2).days)//7
        except:
            spaeter = ((startdatum-d2).days)//7
    else:
        woche_halbjahr = schulwoche
        spaeter = (startdatum - d0).days//7
    if woche_halbjahr < 0:
        woche_halbjahr = 0
    if spaeter < 0:
        spaeter = 0
    soll_hj = aufg2hj[woche_halbjahr] - aufg2hj[spaeter]
    soll_hj = int(soll_hj * aufgaben_pro_woche)                                                 # ist die Anzahl der Aufgaben, die in dieser Woche gerechnet worden sein müssten (pro Schulwoche und Jahrgang des Users 10 - also z.B. 70 pro Woche im Jahrgang 7)
    if soll_hj > 1600:
        soll_hj = 1600
    pflicht_kat = Kategorie.objects.filter(start_sw__lte= schulwoche, start_jg = jg) | Kategorie.objects.filter(start_jg__lt = jg)
    pflicht_kat = pflicht_kat.count()
    if pflicht_kat > 0:
        soll_kat = int(soll_hj/pflicht_kat)
    else:
        soll_kat = 0                 
    if soll_kat < 10:
        soll_kat = 10
    return schulwoche, woche_halbjahr, soll_hj, soll_kat, pflicht_kat

def bewertung_kat(soll_kat, richtig, falsch, lsg, abbr, stufe):
    prozent_kat = 0 if soll_kat == 0 else richtig/soll_kat*100
    if prozent_kat > 110:
        prozent_kat = 110
    if richtig > 0:
        #prozent_kat *= ((richtig-falsch-lsg-abbr)/richtig)
        prozent_kat = (prozent_kat+((richtig-falsch-lsg-abbr)/richtig*100))/2
    if prozent_kat < 0:
        prozent_kat = 0
    prozent_farbe = quote_farbe(prozent_kat,100-prozent_kat,0.5)
    return prozent_farbe, prozent_kat 

def bewertung_hj(prozent_summe, pflicht_kat, stufe):                            # Bewertung + Note für das Halbjahr
    prozent_summe = int(prozent_summe/pflicht_kat)                              # addiert alle Prozentwerte und bildet den Durchschnitt (aus)
    prozent_summe_farbe = quote_farbe(prozent_summe,100-prozent_summe,0.5)
    note = 6 if prozent_summe < 25 else 7-((prozent_summe-stufe%2*5)//15)       # für E-Kurs 1,2,3,4,5 bei 95,80,65,50% für G-Kurs entsprechende Note mit 5% weniger
    plusminus = (prozent_summe+3-stufe%2*5)%15                                  # + oder - bei 3% mehr oder weniger
    if plusminus in range (3,6):
        note = str(note)+"-"
    if plusminus in range (0,3):
        note = str(note)+"+"
    return prozent_summe_farbe, prozent_summe, note 

#Hier werden normalerweise die Aufgaben gestartet
def uebersicht(req, schueler_id=0):
    if req.user.is_authenticated:
        lehrer = User.objects.filter(pk=req.user.id, groups__name='Lehrer').exists()
        loeschen = False 
        if schueler_id == 0:
            profil = get_object_or_404(Profil, user_id = req.user.id)
            if lehrer:
                loeschen = True            
        else:
            profil = get_object_or_404(Profil, id = schueler_id)
        if(profil.id) != (req.user.profil.id):
            if lehrer and (profil.gruppe.lehrer.id) != (req.user.id):
                if req.user.is_superuser:
                    pass
                else:
                    return HttpResponse("Zugriff verweigert")
        protokoll = Protokoll.objects.filter(user=profil, sj=profil.sj, hj=profil.hj)
        if protokoll.count() == 0:                                                                  # noch keine Aufgaben da
            richtig_gesamt = falsch_gesamt= abbr_gesamt= lsg_gesamt= hilfe=gesamt= 0
            #letzte = k['letzte']
        else:
            durchschnitt, richtig_gesamt, falsch_gesamt, abbr_gesamt, lsg_gesamt, hilfe_gesamt = durchschnitt_aufgaben(profil)
        alle = False
        if req.method == 'POST':
            alle = True
        if profil.jg >= 7 or alle:
            kategorien = Kategorie.objects.all().order_by('zeile')                                      # alle kategorien
            alle = True
        elif profil.jg >= 6:
            kategorien = Kategorie.objects.filter(zeile__lt = 22)
        elif profil.jg >= 5:
            kategorien = Kategorie.objects.filter(zeile__lt = 15)
        else:
            kategorien = Kategorie.objects.filter(zeile__lt = 8)
        zeilen = []
        zeit_gesamt = 0
        bearbeitet = 0
        prozent_kat = 0
        breite = "breit"
        sj = profil.sj
        hj = profil.hj
        gruppe = profil.gruppe
        prozent_summe = nicht_richtig_summe =  nicht_richtig_summe_quote = 0
        prozent_summe_farbe = nicht_richtig_summe_farbe = farbe_kat = None
        note = "-"
        bewertung_anzeigen = True
        aufgaben_pro_woche = 10
        if gruppe:
            aufgaben_pro_woche = gruppe.aufgaben_pro_woche
            bewertung_anzeigen = gruppe.note_anzeigen
            if aufgaben_pro_woche < 1:
                aufgaben_pro_woche = 10 * profil.jg
        else:
            aufgaben_pro_woche = 10 * profil.jg
            bewertung_anzeigen = False
        if profil.jg > 10:
            aufgaben_pro_woche = 100
        try:
            details = profil.details
        except:
            details = True
        # wenn die Lerngruppe nach dem Beginn des Halbjahres angelegt wurde, werden von den Sollaufgaben entsprechend abgezogen - ebenso, wenn keine Lerngruppe verknüpft ist, entsprechend mit der Registrierung
        profil_gruppe = profil.gruppe
        if profil_gruppe:
            startdatum = profil.gruppe.erstellt_am
        else:
            startdatum = profil.user.date_joined
        schulwoche, woche_halbjahr, soll_hj, soll_kat, pflicht_kat = soll_berechnung(sj, hj, profil.jg, aufgaben_pro_woche, startdatum)                    # berechnet den Aufgabensoll für das Halbjahr und Kategorie
        for kategorie in kategorien:
            pflicht = False
            falsch_kat = abbr_kat = lsg_kat = hilfe_kat = 0
            nicht_richtig_kat = prozent_kat = 0
            prozent_farbe = nicht_richtg_farbe = None
            if (kategorie.start_jg < profil.jg) or (kategorie.start_sw <= schulwoche and kategorie.start_jg == profil.jg):
                pflicht = True                                                                      # pflicht = Aufgabenkategorie müsste erledigt werden
                kat_farbe = "rot"
            else:
                kat_farbe = None
            index =  kategorie.zeile
            protokoll_kategorie = protokoll.filter(kategorie = kategorie)
            if protokoll_kategorie.count() > 0:                                                     # es sind Aufgaben da
                zaehler_kategorie = Zaehler.objects.get(user=profil, kategorie = kategorie)
                #print(kategorie, zaehler_kategorie.fehler_ab)
                kategorie_werte = (                                                                 # die Summen der einzelnen Kategoren des jeweiligen Users
                    protokoll_kategorie
                    .values("kategorie__zeile")
                    .annotate(richtig_sum=Sum('richtig'))
                    .annotate(zeit_sum=Sum(F('end') - F('start')))
                    )
                for k in kategorie_werte:
                    zeile = [[],[]] 
                    richtig_kat = k['richtig_sum']
                    if richtig_kat >= soll_kat:                                                     # in jeder Schulwoche sollte mindestens 10 * sj Aufgaben richtig gerechnet werden
                        kat_farbe = "gruen"
                    elif richtig_kat >= 10:
                        kat_farbe = "gelb"
                    # elif richtig_kat >= 10 and richtig_kat*2 < durchschnitt and pflicht:          # wenn weniger als die Hälfte der durchschnittlichen Aufgaben gerechnet wurden  
                    #     kat_farbe = "gelb"
                    #print(zaehler_kategorie.fehler_ab.replace(tzinfo=None) < datetime(2024, 1, 1, 0, 0, 0, 0) )  
                    #if zaehler_kategorie.fehler_ab.replace(tzinfo=None) < datetime(2024, 1, 1, 0, 0, 0, 0):
                    falsch_kat = zaehler_kategorie.fehler_zaehler
                    abbr_kat = zaehler_kategorie.abbr_zaehler
                    lsg_kat = zaehler_kategorie.lsg_zaehler
                    hilfe_kat = zaehler_kategorie.hilfe_zaehler  
                    # else:
                    #     fehler_ab = zaehler_kategorie.fehler_ab
                    #     protokoll_fehler = protokoll_kategorie.filter(start__gt=fehler_ab)
                    #     protokoll_fehler = (                                                                 # die Summen der Fehler seit des jeweiligen Users
                    #         protokoll_fehler
                    #         .values("kategorie__zeile")
                    #         .annotate(falsch_kat=Sum('falsch'))
                    #         .annotate(abbr_kat=Sum('abbr'))
                    #         .annotate(lsg_kat=Sum('lsg'))
                    #         .annotate(hilfe_kat=Sum('hilfe'))
                    #         ) 
                    #     for f in protokoll_fehler:
                    #         falsch_kat = f['falsch_kat'] 
                    #         abbr_kat = f['abbr_kat']
                    #         lsg_kat = f['lsg_kat'] 
                    #         hilfe_kat = f['hilfe_kat'] 
                    #         if abbr_kat == True:
                    #             abbr_kat = 1
                    #         elif abbr_kat == False:
                    #             abbr_kat = 0 
                    #         if lsg_kat == True:
                    #             lsg_kat = 1
                    #         elif lsg_kat == False:
                    #             lsg_kat = 0 
                    #         if hilfe_kat == True:
                    #             hilfe_kat = 1
                    #         elif hilfe_kat == False:
                    #             hilfe_kat = 0 
                    qfarbe = quote_farbe(richtig_kat, falsch_kat)
                    zeit_kat = k['zeit_sum']
                    try:
                        zeit_text = int(zeit_kat.total_seconds())
                        if zeit_text <= 60:
                            zeit_text = "<"
                        else:
                            mm = zeit_text//60
                            hh, mm = divmod(mm, 60)
                            zeit_text = f"{hh}:{mm:02d}"
                    except:
                         zeit_text = "-"
                    letzte_kat = zaehler_kategorie.letzte.strftime("%d.%m.%y")
                    abbr_farbe = lsg_farbe = None
                    nicht_richtig_quote = 0
                    if richtig_kat > 0:
                        if lsg_gesamt > 0:
                            if lsg_kat > richtig_kat/10:
                                lsg_farbe = "rot"
                            elif lsg_kat > richtig_kat/20:
                                lsg_farbe ="gelb"
                        if abbr_kat  > 0:
                            if abbr_kat > richtig_kat/10:
                                abbr_farbe = "rot"
                            elif abbr_kat > richtig_kat/20:
                                abbr_farbe ="gelb"
                    if richtig_kat+falsch_kat > 0:
                        quote = int(falsch_kat/(richtig_kat+falsch_kat)*100)
                        try:
                            pro_aufg = round(zeit_kat.total_seconds()/float(richtig_kat+falsch_kat),1)
                        except:
                            pro_aufg = "-"
                        if not details:
                            nicht_richtig_kat = falsch_kat+abbr_kat+lsg_kat
                            nicht_richtig_quote = int(nicht_richtig_kat/(richtig_kat+nicht_richtig_kat)*100)
                    else:
                        quote = "-"
                        pro_aufg = "-"
                    if zeit_kat == None:
                        zeit_kat = '-'
                    else:
                        zeit_gesamt += zeit_kat.seconds
                    prozent_farbe, prozent_kat = bewertung_kat(soll_kat, richtig_kat, falsch_kat, lsg_kat, abbr_kat, profil.stufe)      # berechnet die Wertung der Kategorie
                    if not pflicht or not bewertung_anzeigen:
                        prozent_farbe = None
                    if not pflicht:
                        qfarbe = abbr_farbe = lsg_farbe = None
                        if richtig_kat >= 10:
                            kat_farbe = "gruen"
                        else:
                            kat_farbe = None
                    prozent_summe +=prozent_kat
                    nicht_richtig_summe +=nicht_richtig_kat
                    if details == True:
                        zeile = (kategorie,((kat_farbe,richtig_kat), (None,falsch_kat), (qfarbe,str(quote)+"%"), (None,zeit_text), (None,pro_aufg), (None, str(zaehler_kategorie.richtig_of)+"/"+str(kategorie.eof)), 
                                (abbr_farbe,abbr_kat), (lsg_farbe, lsg_kat), (None,hilfe_kat), (prozent_farbe,str(int(prozent_kat))+"%"), (None,letzte_kat)))
                    else:
                        zeile = (kategorie,((kat_farbe,richtig_kat), (None,nicht_richtig_kat), (qfarbe,str(nicht_richtig_quote)+"%"),  (prozent_farbe,str(int(prozent_kat))+"%")))   
                    bearbeitet = index
            if index != bearbeitet:
                farbe_kat = 'rot' if pflicht else None
                prozent_farbe = 'rot' if pflicht and bewertung_anzeigen else None
                if details == True:
                    zeile = kategorie, ((farbe_kat,'-'), *((None,'-'),) * 8,(prozent_farbe,'0%' if pflicht else '-'),(None,'-'))
                    breite = "breit"
                else:
                    zeile = kategorie, ((farbe_kat,'-'), *((None,'-'),) * 2,(prozent_farbe,'0%' if pflicht else '-'))
                    breite = "schmal"
            zeilen.append(zeile)
        summe_farbe = prozent_summe_farbe = "unset" 
        if richtig_gesamt + falsch_gesamt >0:
            summe_farbe = quote_farbe(richtig_gesamt,soll_hj-richtig_gesamt)
            quote = int(falsch_gesamt/(richtig_gesamt + falsch_gesamt)*100)
            qfarbe = quote_farbe(richtig_gesamt, falsch_gesamt)  
            pro_aufg = format_zahl(zeit_gesamt/(richtig_gesamt + falsch_gesamt),1)
            h, min = divmod(zeit_gesamt, 3600)
            min, sec = divmod(min, 60) 
            dauer = f'{int(h)}:{int(min):02d}'
            if pflicht_kat > 0:
                prozent_summe_farbe, prozent_summe, note = bewertung_hj(prozent_summe, pflicht_kat, profil.stufe)                         # Berechnung der Gesamtnote
            else:
                prozent_summe_farbe = prozent_summe = note = None  
            if not bewertung_anzeigen:
                prozent_summe_farbe = None
            if not details:
                nicht_richtig_summe_quote = int(nicht_richtig_summe/(richtig_gesamt + nicht_richtig_summe)*100)
                nicht_richtig_summe_farbe = quote_farbe(richtig_gesamt,nicht_richtig_summe)
            if soll_hj < 10*pflicht_kat and prozent_summe < 50:
                note = "-"
                prozent_summe_farbe = None
        else:
            richtig_gesamt=falsch_gesamt=zeit_gesamt=abbr_gesamt=lsg_gesamt=hilfe_gesamt=0
            quote = "-"  
            qfarbe = "unset" 
            dauer = '-'
            pro_aufg = "-" 
        context = dict(lehrer= lehrer, loeschen= loeschen, schueler = profil, zeilen= zeilen, soll_hj = soll_hj, pro_woche =aufgaben_pro_woche, soll_kat=soll_kat,
            richtig=richtig_gesamt, summe_farbe= summe_farbe, falsch=falsch_gesamt, quote=quote, qfarbe=qfarbe, dauer=dauer, pro_aufg = pro_aufg, details=details, alle = alle,
            abbr=abbr_gesamt, lsg=lsg_gesamt, hilfe= hilfe_gesamt, prozent_summe_farbe=prozent_summe_farbe, prozent_summe=prozent_summe, note=note, 
            nicht_richtig_summe_farbe=nicht_richtig_summe_farbe, nicht_richtig_summe_quote=nicht_richtig_summe_quote, nicht_richtig_summe=nicht_richtig_summe, breite = breite, bewertung = bewertung_anzeigen)
        # try:
        #     context["letzte"] = letzte.strftime("%d.%m.%y %H:%M")
        # except:
        #     pass
        if details:
            return render(req, 'core/uebersicht.html', context)
        else:
            return render(req, 'core/uebersicht_ohne_details.html', context)
    else:
        return redirect('anmelden')

def protokoll_zeit_filter(protokoll, auswahl):
    sj, hj = name_hj()
    next_sj, next_hj = name_next_hj()
    if auswahl == "next":
        protokoll = protokoll.filter(sj=next_sj, hj=next_hj)  
    if auswahl == "Halbjahr":
        protokoll = protokoll.filter(sj=sj, hj=hj)                               
    elif auswahl == "heute":
        protokoll = protokoll.filter(start__date = date.today())
    elif auswahl == "Woche":
        protokoll =  protokoll.filter(start__date__gte = date.today() - timedelta(days = 7))
    elif auswahl =="Schuljahr":
        protokoll = protokoll.filter(sj = sj) 
    return protokoll

#Hier werden die Aufgaben protokolliert
def protokoll(req, schueler_id=0):
    if req.user.is_authenticated:
        lehrer = User.objects.filter(pk=req.user.id, groups__name='Lehrer').exists()
        loeschen = False 
        if schueler_id == 0:
            user_profil = get_object_or_404(Profil, user_id = req.user.id)          # der Lehrer
            if lehrer:
                loeschen = True            
        else:
            user_profil = get_object_or_404(Profil, id = schueler_id)               # Schülerin oder Schüler
        if(user_profil.id) != (req.user.profil.id) and (user_profil.gruppe.lehrer.id) != (req.user.id) and not req.user.is_superuser:
            return HttpResponse("Zugriff verweigert")
        protokoll = Protokoll.objects.filter(user=user_profil).order_by('id').reverse()  # Protokoll des Users
        next_sj, next_hj = name_next_hj()
        auswahl = "heute"
        wahl = "heute"
        protokoll = protokoll.filter(start__date = date.today())
        if next_hj == user_profil.hj and next_sj == user_profil.sj:
            form = ProtokollFilter_neu
        else:
            form = ProtokollFilter
        if req.method == 'POST':
            protokoll = Protokoll.objects.filter(user=user_profil).order_by('id').reverse()
            auswahl = form(req.POST)
            choices = auswahl.fields['auswahl'].choices
            auswahl_liste = dict(choices)
            if auswahl.is_valid(): 
                auswahl = auswahl.cleaned_data['auswahl']
                protokoll = protokoll_zeit_filter(protokoll, auswahl)
                wahl = auswahl_liste[auswahl]
        temp = protokoll.aggregate(Sum('richtig'))['richtig__sum']
        richtig = temp if temp else  0
        temp = protokoll.aggregate(Sum('falsch'))['falsch__sum']
        falsch = temp if temp else  0
        abbr = protokoll.filter(abbr=True).count()
        try:                                                        # wenn keine Aufgaben gerechnet wurden steht 'None# in richtig und falsch und führt zu einem Fehler
            quote = int(falsch/(richtig+falsch)*100)
        except:
            quote = "-"
        qfarbe =  quote_farbe(richtig, falsch) 
        lsg = protokoll.filter(lsg=True).count()
        hilfe = protokoll.filter(hilfe=True).count()
        #protokoll = protokoll.exclude(end__isnull=True, abbr__isnull=True, eingabe__exact="")
        exclude = ["", " Hilfe "]
        protokoll = protokoll.exclude(eingabe__in = exclude)
        context = dict(lehrer= lehrer, loeschen= loeschen, schueler = user_profil, protokoll= protokoll, form= form, wahl= wahl, 
            richtig=richtig, falsch=falsch, quote=quote, qfarbe=qfarbe, abbr=abbr, lsg=lsg, hilfe = hilfe)
        return render(req, 'core/protokoll.html', context)
    else:
        return redirect('anmelden')

#Hier können die einzelnen Aufgaben genauer analysiert werden . Wird von der Protokollseite aus aufgerufen
def details(req, zeile_id, schueler_id=0):
    protokoll = Protokoll.objects.get(pk = zeile_id)
    if (protokoll.user.id) != (req.user.profil.id) and (protokoll.user.gruppe.lehrer.id) != (req.user.id) and not req.user.is_superuser:
    #if(protokoll.user.id) != (req.user.profil.id):
        return HttpResponse("Zugriff verweigert")
    try:
        hilfe = Hilfe.objects.get(kategorie = protokoll.kategorie, hilfe_id = protokoll.hilfe_id)
    except:
        hilfe = ""
    zaehler = Zaehler.objects.get(user = protokoll.user, kategorie = protokoll.kategorie)
    return render(req, 'core/details.html', {'protokoll': protokoll, 'zaehler': zaehler, 'hilfe': hilfe, 'titel': ""})

#Hier können u.U. Optionen gewählt werden - z:B. ob mit oder ohen Kommazahlen gerechnet wird
def optionen(req, slug):
    kategorie = get_object_or_404(Kategorie, slug = slug)
    form = AuswahlForm(kategorie = kategorie)
    user = get_user(req.user)  
    if req.method == 'POST':
        form = AuswahlForm(req.POST, kategorie = kategorie, user=user)
        if form.is_valid():
            optionen_text = ';'.join(map(str, form.cleaned_data['optionen']))
            if optionen_text == "":
                optionen_text = "keine"
        else:
            optionen_text = "keine"  
    else:
        form = AuswahlForm(kategorie=kategorie, user=user)
        anzahl = kategorie.auswahl_set.all().count()
        if anzahl>0:
            anzahl = Auswahl.objects.filter(bis_jg__gte = user.jg, bis_stufe__gte = user.stufe, kategorie = kategorie).count()
            if anzahl>0:
                return render(req, 'core/optionen.html', {'kategorie': kategorie, 'auswahl_form':form})
            else:
                optionen_text = "keine"    
        else:
            optionen_text = "keine"
    zaehler = get_object_or_404(Zaehler, kategorie = kategorie, user = user)
    zaehler.optionen_text = optionen_text       
    typ_anf, typ_end = aufgaben(kategorie.zeile, jg = user.jg, stufe = user.stufe, optionen = zaehler.optionen_text)
    zaehler.typ_anf = typ_anf
    zaehler.typ_end = typ_end
    zaehler.save()
    return redirect('main', slug)

#Die 10 Aufgaben weden abgebrochen. Dies wird gezählt. Eigentlich wird bei der Erstellung jeweils dieser Zähler hochrechnet und nur wenn eine richtige oder falsche Eingabe erfolgt oder "Lösung anzeigen" 
#angeklickt wird, wird dieser Zähler wieder um Eins zurückgesetzt. Dadurch wird auch als Abbrechen gezählt, wenn z.B. mit F5 eine neue Aufgabe erzeugt wird.
def abbrechen(req, zaehler_id):
    zaehler = get_object_or_404(Zaehler, pk = zaehler_id)
    #zaehler.abbr_zaehler += 1
    zaehler.aufgnr = 0
    zaehler.optionen_text = ""
    zaehler.richtig_of = 0 
    zaehler.hinweis = ""
    zaehler.save() 
    protokoll = Protokoll.objects.filter(user = zaehler.user).order_by('-id').first()
    if protokoll.wertung != "a":
        protokoll.wertung = protokoll.wertung + "a"
    if protokoll.eingabe != "":
        protokoll.eingabe = protokoll.eingabe + ", abbr."
    else:
        protokoll.eingabe = "abbr."        
    protokoll.save()
    return redirect('uebersicht')

#Hier wird die Lösung angezeigt:
def loesung(req, zaehler_id, protokoll_id):
    zaehler = get_object_or_404(Zaehler, pk = zaehler_id)
    zaehler.richtig_of = 0 
    zaehler.lsg_zaehler += 1
    zaehler.save()
    protokoll = get_object_or_404(Protokoll, pk = protokoll_id)
    protokoll.eingabe = protokoll.eingabe + " Lsg. "
    protokoll.wertung = "l"
    protokoll.lsg = True
    protokoll.abbr = False
    protokoll.save()
    eingabe = protokoll.eingabe.replace(" Lsg.","")
    try:
        if isinstance(protokoll.loesung[0], list):
            text = "; ".join(protokoll.loesung[0]).replace(".",",")
        else:
            text = protokoll.loesung[0]
    except:
        text = protokoll.loesung
  
    messages.info(req, f'Lösung: {text}') 
    context = dict(lsg = True, kategorie = protokoll.kategorie, typ = protokoll.typ, titel = protokoll.titel, aufgnr = zaehler.aufgnr, text = protokoll.text, frage = protokoll.frage, eingabe = eingabe,
        message_unten = protokoll.anmerkung,  zaehler_id = zaehler.id, protokoll_id = protokoll.id, parameter = protokoll.parameter, hinweis = "Lösung")
    return render(req, 'core/aufgabe.html', context)

#und hier die Hilfe:
def hilfe(req, zaehler_id, protokoll_id):
    zaehler = get_object_or_404(Zaehler, pk = zaehler_id)
    zaehler.hilfe_zaehler += 1
    zaehler.save()
    protokoll = get_object_or_404(Protokoll, pk = protokoll_id)
    parameter = protokoll.parameter
    try:
        hilfe = get_object_or_404(Hilfe, kategorie = protokoll.kategorie, hilfe_id = protokoll.hilfe_id)
        protokoll.eingabe = protokoll.eingabe + " Hilfe "
        protokoll.hilfe = True
        protokoll.save()
        messages.info(req, hilfe.text.format(*protokoll.variable))  
    except:
        messages.info(req, "Leider gibt es hier keine Hilfe.<br>Der Rechentrainer freut sich, wenn du ihm eine Email schickst, dass die Hilfe mit der Nummer {} fehlt :).".format(protokoll.hilfe_id)) 
        form = AufgabeFormStr(req.POST)
    if "tab" in protokoll.parameter["name"]:
        form = AufgabeFormTab(req.POST)
    else:
        if protokoll.wert:
            form = AufgabeFormZahl(req.POST)
        #wenn in den Aufgaben erg=None:
        else:
            form = AufgabeFormStr(req.POST)
    context = dict(kategorie = protokoll.kategorie, typ = protokoll.typ, titel = protokoll.titel, aufgnr = zaehler.aufgnr, text = protokoll.text, frage = protokoll.frage, einheit = protokoll.einheit, message_unten = protokoll.anmerkung, 
                   form = form, zaehler_id = zaehler.id, protokoll_id = protokoll.id, parameter = parameter)
    parameter["hilfe"] = protokoll.hilfe_id
    return render(req, 'core/aufgabe.html', context)

#Dict zum Zuordnen der kategorie.zeile zu den einzelnen Aufgaben:
AUFGABEN = {
    1: addieren, 2: subtrahieren, 3: verdoppeln, 4: halbieren, 5: einmaleins, 6: kopfrechnen, 7: sachaufgaben, 8: zahlen, 9: malget10, 10: runden, 
    11: regeln, 12: geometrie, 13: einheiten, 14: figuren, 15: kommazahlen, 16: winkel, 17: bruchteile, 18: kuerzen, 19: bruch_komma, 20: bruchrechnung, 
    21: quader, 22: zuordnungen, 23: prozentrechnung, 24: negativ, 25: terme, 26: gleichungen, 27: wahrscheinlichkeit, 28: funktionen}

def aufgaben(kategorie_id, jg = 5, stufe = 3, aufgnr = 0, typ_anf = 0, typ_end = 0, typ = 0, typ2 = 0, optionen = "", eingabe = "", lsg = ""):
    return AUFGABEN[kategorie_id](jg, stufe, aufgnr, typ_anf, typ_end, typ, typ2, optionen, eingabe, lsg)

#hier erfolgt die Kontrolle. Entweder der Zahlenwert oder eine Texteingabe. Falls die Aufgabe hier nicht als richtig gewertet wird, wird u.U. 
#(Wenn in den Lösungen "indiv_0" steht) nochmals individuell in den Funktionen der Kategorien die Eingabe überprüft.
def kontrolle(eingabe, wert, lsg, protokoll_id):
    if wert != None:                                     
        if  decimal.Decimal(eingabe) == wert:
            return 1, ""
        #return abs(given - wert) < decimal.Decimal('0.001') <- das würde man benötigen um Rundungsfehler von Python auszugleichen, ich nutze aber eigentlich nur Ganzahlen
        else:
            if "indiv_0" in lsg:
                protokoll = get_object_or_404(Protokoll, pk = protokoll_id)
                punkte, rueckmeldung = aufgaben(protokoll.kategorie.zeile, eingabe=eingabe, lsg=lsg, typ=protokoll.typ, typ2=protokoll.typ2)
                return punkte, rueckmeldung             #hier wurde festgestellt, dass die Eingabe doch richtig ist                         
            else:
                return -1, ""    
    else:
        if isinstance(eingabe, list):                           # für Wertetabellen
            lsg = lsg[0]
            punkte = 3*10**len(lsg)
            rueckmeldung = ""
            for n in range(len(lsg)):
                if eingabe[n] is not None:                      # überprüft ob Einträge richtig sind
                    if (float(lsg[n].replace(",", "."))) == float(eingabe[n]):
                        punkte += 1*10**(n)
                        rueckmeldung = rueckmeldung + (str(n+1) + ": richtig ")
                    else:
                        rueckmeldung = rueckmeldung + (str(n+1) + ": falsch ")
                else:
                    rueckmeldung = rueckmeldung + (str(n+1) + ": leer ")
                    punkte += 2*10**(n)
            return punkte, rueckmeldung
        else:
            eingabe=eingabe.replace("^2","²")
            protokoll = get_object_or_404(Protokoll, pk = protokoll_id)
            if lsg[-1] == 'indiv_2':                # nur für prozentrechnung und Quader - hier wird der Wert eines Terms berechnet
                parser = Parser()
                try:
                    zahl=round(parser.parse(eingabe.replace(",",".").replace(":","/")).evaluate({}),3)
                    if round(zahl,3) == round((lsg[1]),3):
                        if lsg[-1] == 'indiv_1' or lsg[-1] == 'indiv_2':                   
                                punkte, rueckmeldung = aufgaben(protokoll.kategorie.zeile, eingabe=eingabe, lsg=lsg, typ=protokoll.typ, typ2=protokoll.typ2)
                                return punkte, rueckmeldung
                        return 1, ""
                    else:
                        return -1, ""
                except:
                   return 0, "Da stimmt was nicht - den Term kann ich nicht berechnen"
            for loe in (lsg):
                try:
                    if eingabe.replace(" ","") == loe.replace(" ",""):
                        if lsg[-1] == 'indiv_1' or lsg[-1] == 'indiv_2' :                    #nachdem die Eingabe als richtig bewertet wurde können u.U. Extrapunkte (oder Punktabzüge) geben
                            protokoll = get_object_or_404(Protokoll, pk = protokoll_id)
                            punkte, rueckmeldung = aufgaben(protokoll.kategorie.zeile, eingabe=eingabe, lsg=lsg, typ=protokoll.typ, typ2=protokoll.typ2)
                            return punkte, rueckmeldung
                        return 1, ""
                except:
                    pass
            if "indiv_0" in lsg:                           #wenn in der Liste 'loesungen' 'indiv_0' steht, dann wird der eingegebene Wert in der Funtion der entsprechenden Kategorie überprüft nachdem die normale Routine "kontrolle" keine Gleichheit festgestellt hat.
                protokoll = get_object_or_404(Protokoll, pk = protokoll_id)
                punkte, rueckmeldung = aufgaben(protokoll.kategorie.zeile, eingabe=eingabe, lsg=lsg, typ=protokoll.typ, typ2=protokoll.typ2)
                if punkte > 0:
                    return punkte, rueckmeldung             #hier wurde festgestellt, dass die Eingabe doch richtig ist
                else:
                    if rueckmeldung:
                        return punkte, rueckmeldung         #hier gibt es noch einen Hinweis zur richtigen Eingabe
            return -1, ""                       #ansonsten = falsch

# hier läuft alles zusammen <<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<<
def main(req, slug):
    if req.user.is_authenticated: 
        kategorie = get_object_or_404(Kategorie, slug = slug)
        user = get_user(req.user)
        bis_loeschen = "-"
        titel = ""
        if req.method == 'POST':
            protokoll = Protokoll.objects.get(pk = req.session.get('protokoll_id'))
            protokoll.versuche += 1
            zaehler = Zaehler.objects.get(pk = req.session.get('zaehler_id'))
            zaehler.hinweis = ""
            #wenn in den Aufgaben in "erg" eine Zahl steht
            if "tab" in protokoll.parameter["name"]:
                if "term" in protokoll.parameter["name"]:
                    form = AufgabeFormTerm(req.POST)
                else:
                    form = AufgabeFormTab(req.POST)
            else:
                if protokoll.wert:
                    form = AufgabeFormZahl(req.POST)
                #wenn in den Aufgaben erg=None:
                else:
                    form = AufgabeFormStr(req.POST)
            #Aufgabe beantwortet
            if form.is_valid():  
                # zunächst Einträge im Protokoll:
                if "tab" in protokoll.parameter["name"]:                            # für Wertetabellen
                    eingabe = []
                    if "term" in protokoll.parameter["name"]:                            # für Terme
                        eingabe.append(form.cleaned_data['y0'])
                        eingabe.append(form.cleaned_data['y1'])
                    eingabe.append(form.cleaned_data['y2'])
                    eingabe.append(form.cleaned_data['y3'])
                    eingabe.append(form.cleaned_data['y4'])
                    pro_eingabe = "; ".join([str(e) for e in eingabe]).replace(".",",")
                else:
                    eingabe = pro_eingabe = form.cleaned_data['eingabe']
                if protokoll.versuche == 1:
                    protokoll.eingabe = pro_eingabe
                elif protokoll.versuche == 2:
                    protokoll.eingabe ="(1:) {}; (2:) {}".format(protokoll.eingabe, pro_eingabe)
                else:
                    protokoll.eingabe = "{}; (3:) {}" .format(protokoll.eingabe, pro_eingabe) 
                #bei der Erstellung der Aufgabe wird der Abbrechen_zähler um Eins hochgezählt, wenn eine Eingabe erfolgt wird das hier wieder rückgängig gemacht.
                #Dadurch wird der Zähler hochgesetzt, wenn mit F5 eine neue Aufgabe erzeugt wird.
                protokoll.abbr = False
                if protokoll.wertung == "a": 
                    protokoll.wertung = "" 
                    zaehler.abbr_zaehler -= 1  
                protokoll.end = timezone.now()
                protokoll.save()
                #hier wird die Eingabe überprüft:
                wertung, rueckmeldung = kontrolle(eingabe, protokoll.wert, protokoll.loesung, protokoll.id)
                if wertung <= 2:
                    tabelle = 0
                    richtig = wertung
                else:
                    if wertung >= 3000:                                   # Anzahl der Einträge in der Tabelle
                        tabelle = 3
                        richtig = str(wertung).count("1")
                        falsch = str(wertung).count("0")
                    if wertung >= 300000:
                        tabelle = 5
                #wenn Eingabe richtig:
                if (wertung > 0 and tabelle == 0) or (richtig == tabelle and tabelle > 0) :
                    if tabelle > 0:                  # alle Eingaben in der Tabelle richtig
                        rueckmeldung = "Alle Werte waren richtig richtig!"
                        zaehler.richtig_of += tabelle
                        zaehler.aufgnr += tabelle
                        # entfernt eventuelle Einträge "r"
                        protokoll.wertung = protokoll.wertung.replace("r", "") + richtig*"r"
                    elif tabelle == 0 :
                        if "enauer" in rueckmeldung:
                            rueckmeldung = "Die letzte Aufgabe war fast richtig!"+ rueckmeldung
                        else:
                            rueckmeldung = "Die letzte Aufgabe war richtig!"+ rueckmeldung
                        zaehler.richtig_of += 1
                        zaehler.aufgnr += 1                                                                         
                        protokoll.wertung = protokoll.wertung + "r"
                    if zaehler.richtig_of >= kategorie.eof:                 # wenn die erforderliche Anzahl richtiger Antworten eingegeben wurde, wird der jeweilige Fehlerzähler zurückgesetzt
                        if zaehler.fehler_zaehler > 0:
                            rueckmeldung = rueckmeldung + "<br><b>Herzlichen Glückwunsch: Dein Fehlerzähler wurde zurückgesetzt!</b>"
                        zaehler.fehler_ab = timezone.now()
                        zaehler.fehler_zaehler = 0
                        zaehler.lsg_zaehler = 0
                        zaehler.hilfe_zaehler = 0
                        zaehler.abbr_zaehler = 0
                    protokoll.richtig = richtig                        
                    protokoll.save()
                    zaehler.save()
                    #nach 10 Aufgaben geht es zurück zur Übersicht - eine neue Kategorie kann gewählt werden:
                    if zaehler.aufgnr > 10:
                        if  zaehler.optionen_text not in ["", "keine",] and user.stufe > 1:         #setzt Stufe hoch wenn eine Option angekreuzt wurde und in der Option "update" = True - nur wenn stufe > 1 (Nicht bei Förder- und Grundschule)
                            max_stufe = 3
                            for auswahl in Auswahl.objects.filter(
                                kategorie=kategorie,
                                text__in=zaehler.optionen_text.split(";"),
                                ).all():
                                if(auswahl.bis_stufe) >= int(user.stufe) and auswahl.update:
                                    user.stufe = auswahl.bis_stufe+1+int(user.stufe)%2
                                    user.save()
                        zaehler.optionen_text = ""
                        zaehler.hinweis = ""
                        zaehler.aufgnr = 0
                        zaehler.letzte = timezone.now()
                        zaehler.save()
                        return redirect('uebersicht')
                    messages.info(req, f'{rueckmeldung}')# {msg}')
                    return redirect('main', slug)
                #wenn Aufgabe falsch:
                else: 
                    #hier wird die aktuelle Aufgabe ausgelesen:
                    titel = protokoll.titel
                    text = protokoll.text
                    parameter = protokoll.parameter
                    anmerkung = protokoll.anmerkung
                    frage = protokoll.frage
                    einheit = protokoll.einheit
                    hilfe_id = protokoll.hilfe_id
                    if tabelle > 0:                                 # Auswertung der Wertetabelle:
                        str_wertung = (str(wertung)[1:]).replace("1","r").replace("0","f").replace("2","/")
                        zaehler.richtig_of = 0
                        zaehler.fehler_zaehler += falsch
                        protokoll.wertung = str_wertung
                        if protokoll.falsch < falsch:
                            protokoll.falsch = falsch
                        protokoll.richtig = richtig
                        protokoll.save()
                        messages.info(req, f'{rueckmeldung}')
                        color_wertung = (str(wertung)[1:]).replace("1","richtig,").replace("0","falsch,").replace("2","leer,")
                        color_wertung =color_wertung[:-1].split(",")
                        y_farbe = {}
                        if tabelle == 5:
                            for n in range (0,tabelle):
                                y_farbe["color" + str(n)] = color_wertung[tabelle-1-n]
                        else:
                            for n in range (0,tabelle):
                                y_farbe["color" + str(n+2)] = color_wertung[tabelle-1-n]
                        parameter.update(y_farbe)
                    if protokoll.versuche >= 3:
                        zaehler.aufgnr += tabelle
                        zaehler.save()                                           
                        messages.info(req, "Leider war deine Eingabe dreimal falsch!<br>Richtig wäre die Lösung: {0} <br>- Frage mal jemanden der dir das erklärt!".format(protokoll.loesung[0])) 
                        anmerkung = "dreimal"
                    else:
                        if wertung < 0:                             #wenn mithilfe des Eintrags "indiv_1" ein Teilpunkt vergeben wurde, wird dies hier angezeigt:
                            messages.info(req, rueckmeldung)  
                            wertung = -1      
                        if wertung == -1:
                            protokoll.falsch = 1
                            protokoll.wertung = "f"
                            protokoll.save()
                            zaehler.richtig_of  = 0
                            zaehler.fehler_zaehler +=1
                            zaehler.save()
                            #nach drei Falscheingaben wird die richtige Lösung angezigt und anschließend die Übersichtsseite aufgerufen:
                            if protokoll.versuche >= 3:                                           
                                messages.info(req, "Leider war deine Eingabe dreimal falsch!<br>Richtig wäre die Lösung: {0} <br>- Frage mal jemanden der dir das erklärt!".format(protokoll.loesung[0])) 
                                anmerkung = "drei"
                            else:
                                messages.info(req, f'Die letzte Aufgabe war leider falsch! Versuche: {protokoll.versuche}')#, {msg}') 
                        else:
                            if not "tab" in protokoll.parameter["name"]:
                                messages.info(req, f'{rueckmeldung}')   #gibt eine Rückmeldung wenn "indiv" bei Lösung steht  
        #hier wird die Aufgabe erstellt:
        else:
            zaehler, created = Zaehler.objects.get_or_create(user = user, kategorie = kategorie)
            gerechnet = Protokoll.objects.filter(richtig__gte = 1, user=user, kategorie = kategorie, sj = user.sj, hj = user.hj).count()
            zaehler = Zaehler.objects.get(user=user, kategorie = kategorie)
            durchschnitt, richtig_gesamt, falsch_gesamt, abbr_gesamt, lsg_gesamt, hilfe_gesamt,  = durchschnitt_aufgaben(user)
            zaehler.sj = user.sj
            zaehler.hj = user.hj
            if created:
                #zaehler.fehler_ab = timezone.now()
                if user.katmax <= kategorie.zeile:
                    user.katmax=kategorie.zeile
                    user.save()             # speichert die höchste gewählte Aufgabenkategorie
            zaehler.save()
            if zaehler.aufgnr == 0:     # Das ist jeweils die erste Aufgabe von 10
                zaehler.aufgnr = 1
                # messages.info(req, "Los geht's")
                zaehler.zeit_summe = 0
                if richtig_gesamt > 100:
                    if gerechnet >= durchschnitt*2 and zaehler.fehler_zaehler == 0 and not user.user.groups.filter(name='Lehrer').exists():                   # Hinweis bei zu vielen Aufgaben
                        return render(req, 'core/genug.html', {'kategorie': kategorie.name})                    
            #hier wird die entsprechende Funktion aufgerufen und festgelegt, aus welchem Bereich (Typ) Aufgaben erzeugt werden
            #zunächst wird überprüft, ob für diese kategorie Einträge bei "Optionen" vorhanden sind:
            if not zaehler.optionen_text :  
                return redirect('optionen', slug)
            #!!!!!!!! hier wird dann die nächste Aufgabe erzeugt: 
            if kategorie.slug == "sachaufgaben":
                try:  
                    user.voreinst["sachaufg"] = user.voreinst["sachaufg"] + 1
                except:                                       
                    user.voreinst.update({"sachaufg" : random.randint(1,20)})
                user.save()
                typ_anf = user.voreinst["sachaufg"]
            else:
                typ_anf = zaehler.typ_anf            
            stufe = user.stufe
            #unter Umständen gibt es auch spezielle Aufgaben für A-Kurs und Gymnasium - dazu wird hier die Stufe um 0,2 hochgesetzt
            if kategorie.name in ("Prozentrechnung","Bruchteile"):
                if user.kurs == "A" or user.kurs == "Y":
                    stufe = stufe + 0.2
            typ, typ2, titel, text, pro_text, frage, variable, einheit, anmerkung, lsg, hilfe_id, ergebnis, parameter = aufgaben(kategorie.zeile, jg = user.jg, stufe = stufe, aufgnr = zaehler.aufgnr, typ_anf = typ_anf, typ_end = zaehler.typ_end, optionen = "") 
            if kategorie.slug == "sachaufgaben":
                user.voreinst["sachaufg"] = typ
                user.save()
            #falls kein Titel angegeben wird, wird der Name der Kategorie verwendet:
            if not titel:
                titel = kategorie.name
            #Hier wird der Aufgabentext erzeugt:
            text = text.format(*variable)
            #u.U. gibt es einen kürzeren Aufgabentext, der auf der Protokollseite angezeigt wird ("prp_text"):
            if pro_text != "" :
                pro_text = pro_text.format(*variable)
            #Die Frage steht vor dem Eingabefeld:
            # if kategorie.name == "Wahrscheinlichkeit" and typ == 0:
            #     pass            # sonst wird ein fehler geworfen da 
            # else:
            frage = frage.format(*variable)
            #Der "Abbrechen" Zähler wird bei jeder Aufgabe hochgesetzt und nur bei einer Eingabe wieder zurücgezählt. 
            #Falls mittels Browser reset eine neue Aufgabe erzeugt wird, wird dies als Abbrechen gewertet.
            zaehler.abbr_zaehler += 1              
            zaehler.save() 
            bis_loeschen = kategorie.eof - zaehler.richtig_of
            #Alle Angaben der Aufgaben wird in einem Eintrag in "Protokoll" gespeichert:
            protokoll = Protokoll.objects.create(
                user = user, titel = titel, sj = user.sj, hj = user.hj, kategorie = kategorie, text = text, pro_text = pro_text, variable = variable, frage = frage, einheit = einheit, 
                anmerkung = anmerkung, wert = ergebnis, loesung = lsg, hilfe_id = hilfe_id, parameter = parameter, wertung = "a", typ = typ, typ2 = typ2, aufgnr = zaehler.aufgnr,        
            )                                                                   #Protokoll wird erstellt
            req.session['protokoll_id'] = protokoll.id    
            req.session['zaehler_id'] = zaehler.id 
            #Jenachdem, ob ein Wert oder ein Text erwartet wird:
            if "tab" in protokoll.parameter["name"]:
                if "term" in protokoll.parameter["name"]:
                    form = AufgabeFormTerm(req.POST)
                else:
                    form = AufgabeFormTab(req.POST)
            else:
                if protokoll.wert:
                    form = AufgabeFormZahl(req.POST)
                #wenn in den Aufgaben erg=None:
                else:
                    form = AufgabeFormStr(req.POST)
        context = dict(kategorie = kategorie, typ = protokoll.typ, titel = titel, aufgnr = zaehler.aufgnr, text = text, frage = frage,
            form = form, zaehler_id = zaehler.id, hilfe = hilfe_id, protokoll_id = protokoll.id, parameter = parameter, message_unten = anmerkung, einheit = einheit, bis_loeschen = bis_loeschen)
        return render(req, 'core/aufgabe.html', context)
    else:
        return redirect('anmelden')


