import math, string, random, re
from math import gcd
from fractions import Fraction

from py_expression_eval import Parser

from .geometrie import sub_koordinatensystem

# Zahlen
def format_zahl(wert, stellen=2, trailing_zeros=True):
    text = f"{wert:.{stellen}f}".replace(".", ",")
    return text.rstrip(",0") if not trailing_zeros and "," in text else text

def zahlzustring(zahl):
    s = f"{zahl:.3f}".rstrip("0").rstrip(".")
    return s.replace(".", ",")

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

def zweizufallszahlen(typ):
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
        random.shuffle(zuza)
        zahl2 = zuza[0] * 10**n + zahl2  
    return zahl1, zahl2

# Brüche
def gemischte_zahl(zaehler, nenner):
    if zaehler%nenner == 0:                                                             # ganze Zahl
        term_a = term_b =str(zaehler // nenner) 
    elif zaehler//nenner != 0:                                                          # gemischte Zahl
        term_a = str(zaehler // nenner) + " " + str(Fraction(zaehler%nenner,nenner))
        term_b = str(zaehler // nenner) + "+" + str(Fraction(zaehler%nenner,nenner))
    else:                                                                               # echter Bruch
        term_a = term_b  = str(Fraction(zaehler,nenner))
    return term_a, term_b

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

def vorzeichen_zahl(wert, stellen=2, trailing_zeros=True):
    text = f"{wert:+.{stellen}f}".replace(".", ",")
    return text.rstrip(",0") if not trailing_zeros and "," in text else text

# Terme
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
        if e+e in term :
            rueckmeldung = 'Anstelle von "{}" schreibt man "{}²".<br>'.format(e+e,e)
    for t in term:
        if t not in erlaubt:
            nicht_erlaubt.append("'"+t+"'")
    if len(nicht_erlaubt) == 1:
        falsch = ",".join(nicht_erlaubt)
        rueckmeldung += 'Das Zeichen {} gehört nicht in den Term.'.format(falsch)
    if len(nicht_erlaubt) > 1:
        falsch = " und ".join(nicht_erlaubt)
        rueckmeldung += ' Die Zeichen {} gehören nicht in den Term.'.format(falsch)    
        return ("", rueckmeldung)
    # if "1^2" in term or "1²" in term:
    #     return 0, "1² = 1"
    term = term.replace("+", " +").replace("-"," -").replace("*","")
    teile = term.split(' ')
    n = 0
    for t in teile:
        if (re.search(r'[\d]²',t)):
            return 0, "{} musst du ausrechnen.".format(t)
        if not (re.search(r'1[\d]',t)) and (re.search(r'1[\D]',t)) and "1" and not "1)" in t:
            teile[n] = teile[n].replace("1","")
            t = t.replace("1","")
            rueckmeldung += '<br>Die "1" lässt man hier weg und schreibt nur "{}"<br>'.format(t)
        n +=1
    term = "".join(teile)
    if typ == 6:
        if "(" not in term:
            return 0, "Wo ist die Klammer?"
        try:
            teile = term.split("(")
            klammer = teile[1]                                          # selektiert die klammer
            klammer = klammer.replace("+", " +").replace("-"," -").replace(")","")
            klammer = klammer.strip()
            teile = klammer.split(' ')                                  # teilt den Klammerinhalt
            for e in erlaubt[:9]:
                if e in teile[0] and e in teile[1]:
                    return 0,  '"{}" musst du auch noch ausklammern.'.format(e)
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
                        return 0,  'Du musst noch den ggT aus {} und {} ausklammern.'.format(zahl1,zahl2)
            except:
                pass
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

#Wertetabellen
def sub_wertetabelle(parameter,stufe):
    zahlen = [0,1,2,-1,0.5]
    zahlen.append(random.randint(-2,2))                                            # nur für das Duell
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
    x_werte = {}
    y_werte = {}
    y_farbe = {}
    lsg = []
    for n in range (0,6):
        x_werte["x" + str(n)] = zahlen[n]
        y_werte["y" + str(n)] = zahlen[n]*koeffizient+absolut
        #y_farbe["color" + str(n)] = "leer"
        lsg.append(str(zahlen[n]*koeffizient+absolut))
    lsg = [lsg]
    parameter.update(x_werte)
    parameter.update(y_werte)
    parameter.update(y_farbe)
    return parameter, term, koeffizient, absolut, lsg

# Funktionsgleichungen
def sub_funktionsgleichung(typ2):
    if typ2 == 1:                               # nur ganze Zahlen
        basis = 1
        absolut_max = 6
        steigung = 0
        while steigung == 0:
            steigung = random.randint(-2,3)
        str_steigung = str(steigung)   
    elif typ2 == 2:                             
        absolut_max = 4
        typ3 = random.randint(1,2)
        if typ3 == 1:                           # Steigung als Bruch
            basis = 3
            steigung = 2/3
            str_steigung = "2/3"
        else:                                   # Kommazahlen ( ,5)
            basis = 4
            steigung = 3/4
            str_steigung = "3/4"
    else:
        basis = 1                       # die Grundlinie des Steigungsdreiecks
        absolut_max = 6
        steigung = 0
        while steigung == 0:
            steigung = random.randint(-4,6)/2
        str_steigung = str(steigung)
    absolut = random.randint(-4,absolut_max)/2
    if absolut == 0:
        gleichung = "{}x".format(str_steigung).replace(".",",").replace(",0","").replace("1x","x")
    else:
        gleichung = "{}x{:+1.1f}".format(str_steigung, absolut).replace(".",",").replace(",0","").replace("1x","x")
    return gleichung, steigung, absolut, basis 

def sub_wertetabelle_quadfu(parameter,stufe):
    zahlen = [0,1,2,-1]
    zahlen.append(random.randint(-2,2))                                            # nur für das Duell
    absolut = koeffizient = 0
    while absolut == 0:
        absolut = random.randint(-4,4)
    koeffizient = random.randint(-4,4)                          # für quadratische Funktionen
    term = "x²{:+d}x{:+d}".format(koeffizient, absolut).replace("+0x","").replace("+1x","+x").replace("-1x","-x")
    x_werte = {}
    y_werte = {}
    #y_farbe = {}
    lsg = []
    for n in range (0,5):
        x_werte["x" + str(n)] = zahlen[n]
        y_werte["y" + str(n)] = zahlen[n]*koeffizient+absolut
        lsg.append(str(zahlen[n]**2+zahlen[n]*koeffizient+absolut))
    lsg = [lsg]
    parameter.update(x_werte)
    parameter.update(y_werte)
    return parameter, term, koeffizient, absolut, lsg

def sub_parabel(p,q):
    box_hoehe = 360
    box_breite = 400
    grid = 20
    y_null = box_hoehe-140          # y_Null  Lage der x-Achse
    x_null = 140                    # x_Null  Lage der y-Achse
    parameter = sub_koordinatensystem(x_null, y_null)
    graph = {'object': 'quadfu', 'p':p*40, 'q':-q*40}
    parameter.update(graph)
    return parameter     

def sub_2werte_pruefen(eingabe,wert,trenner = ";"):
    # zahl=(x1*10+20)*1000+x2*10                  # hier wird eine vierstellige Zahl erzeugt, die später genutzt wird, umd auch Ergebnisse ohne Komma als richtig zu erkennen
    try:
        eingabe=eingabe.split(trenner)
        x1 = float(eingabe[0].replace(",","."))
        x2 = float(eingabe[1].replace(",","."))
        if int(x1*10+20)*1000+int(x2*10) == wert:
            return 1, ""
        if int(x2*10+20)*1000+int(x1*10) == wert:
            return 1, ""
        else:    
            return -1, "" 
    except:
        return 0, "Mit deiner Eingabe stimmt etwas nicht."

def sub_normalform(p,q):
    #normalform = "x²{:+2.1f}x{:+2.1f}".format(-2*p,p**2+q).replace(".0","").replace("1x","x").replace("-0x","").replace(".",",")
    m = -2*p
    n = p**2+q
    normalform = "x²"
    if m !=0:
        normalform += f"{m:+.{2}f}".replace(".0", "").rstrip("0")
        normalform +="x"
    if n !=0:    
        normalform += f"{n:+.{2}f}".replace(".0", "").rstrip("0")
    normalform = normalform.replace(".", ",").replace("1x", "x").replace(".", ",")
    return normalform

def sub_potenz():
    basis = random.randint(0,13)
    if basis in (1,2,10):
        exponent = random.randint(0,5)
    elif basis in (3,4,5):
        exponent = random.randint(2,4)
    else:
        exponent= 2
    return basis, exponent

def sub_potenzterm_mal(typ2, summen = [0,]*5):
    faktor = wert = 1
    frage = lsg = ""
    variablen = ["a","b","c","zahl","zahl"]
    if typ2 != 3:                                        # nur Buchstaben
        variablen = variablen[:3]
    exponenten = [1,2,3]
    if typ2 < 3:
        von = 3
        bis = 4
    else:
        von = 2
        bis = 3
    faktoren = random.randint(von,bis)
    n = 0
    while n < faktoren:
        zuza = random.randint(0,len(variablen)-1)
        variable = variablen[zuza]
        if variable == "zahl":
            zahl = random.randint(2,4)
            faktor *= zahl
            wert *=zahl
            frage +=str(zahl) + "·"
        else:
            exponent = random.choice(exponenten)
            if typ2 == 4:
                exponent *= -1
            summen[zuza] += exponent
            if typ2 == 3:
                koeff = 0
                while koeff == 0:
                    koeff = random.randint(-2,3)
                faktor *= koeff
            if abs(exponent) == 2:
                str_exponent = "²"
            elif abs(exponent) == 3:
                str_exponent = "³"
            else:
                str_exponent = ""
            if typ2 == 3:
                teil="("+str(koeff)+variable+str_exponent+")·"
                teil = teil.replace("(1","(").replace("(-1","(-")
                if koeff > 0:
                    teil = teil.replace("(","").replace(")","")
                frage += teil
            else:
                frage +=variable+str_exponent+"·"
        n += 1 
    frage = frage[:-1]
    n = 0
    while n < len(summen):
        if summen[n] > 0:
            lsg += variablen[n] + "^" + str(summen[n]) + " "
            wert *= (ord(variablen[n])-94)**summen[n]
        n +=1
    lsg = lsg.replace("^1","")#.replace("^2","²").replace("^3","³") 
    if faktor != 1 and faktor != 0:
        lsg = " " + str(faktor) + " " + lsg
        lsg = lsg.replace("-1","-")
    return frage, lsg, wert, faktor, summen

def sub_potenzterm_plus():
    if random.random() < 0.5:    
        variablen = ["zahl","zahl","a ","a²","a³","b ","b²","b³","c ","c²","c³"]
        abzgl = 94
    else:
        variablen = ["zahl","zahl","x ","x²","x³","y ","y²","y³","z ","z²","z³"]
        abzgl = 117
    summen = [0,]*11
    frage = lsg = ""
    wert = 0
    n = 0
    while frage.count(variablen[2])<2 and frage.count(variablen[3])<2 and frage.count(variablen[4])<2 and frage.count(variablen[5])<2 and frage.count(variablen[6])<2 and frage.count(variablen[7])<2 and frage.count(variablen[8])<2 and frage.count(variablen[9])<2 and frage.count(variablen[10])<2:
        zuza = random.randint(0,10)
        koeff = random.randint(1,3)
        variable = variablen[zuza]
        summen[zuza] += koeff
        if variable == "zahl":
            frage += str(koeff) + "+"
            wert += koeff
        else:
            if "²" in variable:
                zwischenwert = ((ord(variable[0]))-abzgl)**2
            elif "³" in variable:
                zwischenwert = ((ord(variable[0]))-abzgl)**3
            else:
                zwischenwert = (ord(variable[0]))-abzgl
            wert += zwischenwert*koeff
            if koeff == 1:
                frage += variable + "+"
            else:
                frage += str(koeff) + variable + "+"
        n += 1
    summen[1] += summen[0]
    n = 1
    while n < len(summen):
        if summen[n] >0:
            if n == 1:
                lsg += str(summen[n])+"+"
            else:
                lsg += str(summen[n]).replace("1","")+variablen[n]+"+"
        n +=1
    frage = frage[:-1]
    frage = frage.replace(" +","+")
    lsg = lsg.replace(" +", "+")
    lsg = lsg[:-1]
    return frage, lsg, wert

def sub_zeichenzuviel(eingabe):
    nachricht = ""
    zeichen = ["*","·","^1"]
    for z in zeichen:
        if z in eingabe:
            nachricht = "Lass das " + z + "weg"
    return nachricht
