import math, decimal, string, random, re

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
            lsg = ["Würfel", "Wuerfel", "Kubus"]                                                  
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
            lsg = ["Pyramidenstumpf","Prisma"]
            anmerkung = ""
            hoehe = random.randint(10,15)*10
            tiefe = breite_u*2
            breite_o = breite_u - random.randint(15,20)
            v = int((breite_u - breite_o)/8)
            v = v*int(hoehe/65)
        box_hoehe = hoehe + (tiefe*0.4) + 10
        if jg == -1 and typ2 == 6:                                            # geändert
            box_hoehe += 30
        y0 = box_hoehe -5#-int((hoehe + int (tiefe*0.4))/2)
        x0 = int((box_breite - tiefe*0.35)/2)
        x11 = x0 - breite_u
        x12 = x0 + breite_u
        x13 = x0 + breite_o - v + w
        x14 = x0 - breite_o + v + w
        x21 = x11 + int(tiefe*0.35)
        x22 = x12 + int(tiefe*0.35)  
        x23 = x13 + int(tiefe*0.25)        
        x24 = x14 + int(tiefe*0.30)
        y11 = y12 = y0
        y13 = y14 = y11 - hoehe
        y21 = y22 = y11 - int(tiefe*10/hoehe) 
        y23 = y24 = y21 - hoehe
        if typ2 == 6 and jg != -1:
            x23 = x23 - 2*v 
            x24 = x24 - 2*v  
            y13 = y13 - int(2.7*v)
            y14 = y14 - int(2.7*v)
            y23 = y23 + int(2.7*v) 
            y24 = y24 + int(2.7*v) 
        if jg == -1 and typ2 == 6:
            box_hoehe = hoehe + tiefe*0.6 + 50   # geändert
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
        anmerkung = anmerkung + "<br>Achte auf die korrekte Schreibweise."
    lsg = lsg + ["indiv_0"]                                                 #sorgt dafür, dass die Eingabe nochmals in der Funktion der Aufgabe überprüft wird                             
    parameter.update(parameter_2)
    return typ2,  hilfe_id, anmerkung, lsg, parameter    

def sub_koordinatensystem(x_null, y_null, box_breite=400, box_hoehe=360, grid=20, einteilung=2):
    parameter = {'name': 'svg/koosys.svg',
            'box_hoehe' : box_hoehe, 'box_breite' : box_breite,
            'grid' : grid,
            'einteilung': einteilung,
            'y_null': y_null,'x_null': x_null,
            }
    if einteilung == -10:
        x_ende = 0
        y_ende = +2
    elif einteilung == 1:
        x_ende = -1
        y_ende = -1
    else:
        x_ende = 0
        y_ende = 0        
    beschriftung = {
        'xvalues': [
            (x_null + n*grid*abs(einteilung), n) for n in range(-x_null//(grid)+2, (box_breite-x_null)//(grid*abs(einteilung))+x_ende)
        ],
        'yvalues': [
            (y_null - n*grid*abs(einteilung), n) for n in range(-(box_hoehe-y_null)//(grid)+2, (y_null)//(grid*abs(einteilung))+y_ende)
        ],
        }                                  # 'n+1%2*n' anstelle von 'n' würde nur die geraden zahlen anzeigen
    parameter.update(beschriftung)
    return parameter

def sub_punkt_pruefen(eingabe, loesung):
    try:
        if "(" not in eingabe or not ")" in eingabe:
                return 0, "Du musst die Koordinaten in Klammern eingeben."
        elif not (";" in eingabe or "|" in eingabe) :
            return 0, "Du musst die Koordinaten mit ';' trennen."        
        else:
            eingabe=eingabe.replace("(","").replace(")","").replace(",",".")
            if ";" in eingabe:
                eingabe=eingabe.split(";")
            elif "|" in eingabe:
                eingabe=eingabe.split("|")
            elif ":" in eingabe:
                eingabe=eingabe.split(":")
            zahl=(float(eingabe[0])*-10+20)*1000
            zahl = zahl + float(eingabe[1])*10
            if zahl == float(loesung):
                return 1, ""
        return 0, "" 
    except:
       return 0, "Mit deiner Eingabe stimmt etwas nicht."

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

# Vierecke
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

# Dreiecke   
def sub_dreieck(typ2):
    breite = random.randint(2,6)
    hoehe = random.randint(2,6)  
    if typ2 == 1:
        x1 = random.randint(4,11-breite)
        y1 = random.randint(1,11-hoehe) 
    else:
        x1 = random.randint(-4,9-breite)
        y1 = random.randint(-4,9-hoehe) 
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
            lsg = ["stumpfwinkliges Dreieck","stumpfwinkliges", "stumpfwinklig"]
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
        anmerkung = anmerkung + "<br>Achte auf die korrekte Schreibweise."
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
    parameter = {'name': 'svg/dreiecke.svg', 'object': 'dreieck', 'winkel': winkel, 'rotate': rotate, 'box_hoehe': box_hoehe, 'box_breite': box_breite, 'breite': breite,
        'x1':x1, 'y1':y1,'x2':x2, 'y2':y2,'x3':x3, 'y3':y3,
        'ecken': [
            (xkoo[n]+ecken_x[n], ykoo[n]+ecken_y[n], ecken[n]) for n in (range(0,3))
        ],
        'seiten': [
            ((xkoo[n]+xkoo[n+1])/2+seiten_x[n], (ykoo[n]+ykoo[n+1])/2+seiten_y[n], seiten[n]) for n in range(0,3)
            ],
    } 
    #lsg = lsg + ["indiv_0"]    
    return typ2, text, frage, einheit, hilfe_id, anmerkung, lsg, parameter

# rechtwinklige Dreiecke
def sub_hypo_oben(g, h, typ2 = 0, scale = 22, x0 = 80, t = 0):
    rand = 25
    h = h * scale
    g = g * scale
    t = t * scale
    spiegeln = 0
    if typ2 >= 1:
        spiegeln = g
    parameter = {'ax': x0,  'ay': h + rand, 'bx': x0 + g, 'by': h + rand, 'cx': x0 + spiegeln, 'cy': rand, 'mx': x0 + (g/2), 'my': h/2 + rand, }
    if typ2 == 0:                               # Hypotenuse rechts oben
        parameter['nx'] = x0 + g/2
        parameter['ox'] = x0
    elif typ2 == 1:                             # Hypotenuse links oben
        parameter['nx'] = x0 + g
        parameter['ox'] = x0 + g/2
    elif typ2 == 2:                             # Häuschen mit Dach
        parameter['axs'] = x0 + g *2
        parameter['ex'] = x0 + math.sqrt(g**2+h**2)
        parameter['winkel'] = -math.atan(h/g)*180/math.pi
        parameter['dy'] = rand + h + t
    elif typ2 == 3:                             # Trapez
        parameter['bx'] = parameter['axs'] = x0 + g*2 + t
        parameter['cx'] = x0 + g + t
        parameter['dx'] = x0 + g
        parameter['nx'] = x0 + g +t/2
        parameter['ex'] = x0 + math.sqrt(g**2+h**2)
        parameter['winkel'] = -math.atan(h/g)*180/math.pi

        parameter['dy'] = parameter['ay']

    return parameter

def sub_hypo_unten(x0, scale, q, p, h):
    rand = 20
    radius = 25
    p = p * scale
    q = q * scale
    h = h * scale
    c = p+q
    parameter = {'ax': x0, 'ay': h + rand, 'bx': x0 + c, 'by': h + rand, 'cx': x0 + q, 'cy': rand, 'mx': x0 + (c/2), 'my': h/2 + rand, 'dy': h*2 + rand}
    #if punkt:
    phi = math.atan(h/q)
    punktwinkel = (phi-math.pi/4)
    c_sx = q - radius * math.cos(phi)
    c_sy = radius * math.sin(phi)
    c_ex = q + radius * math.sin(phi)
    c_ey = radius * math.cos(phi)
    punkt_x = q + radius/2 * math.sin(punktwinkel)
    punkt_y = radius/2 * math.cos(punktwinkel) 
    rechter_winkel = {'c_sx': c_sx + x0, 'c_sy': c_sy + rand, 'c_ex': c_ex + x0, 'c_ey': c_ey + rand, 'punkt_x': punkt_x + x0, 'punkt_y': punkt_y + rand}        
    parameter.update(rechter_winkel)
    return parameter

def sub_rechtwinklig_hypo_unten(x0, scale, a, b, c, p, q, h):
    rand = 20
    radius = 25
    a, b, c, p, q, h = (x * scale for x in (a, b, c, p, q, h))
    parameter = {'ax': x0, 'ay': h + rand, 'bx': x0 + c, 'by': h + rand, 'cx': x0 + q, 'cy': rand, 'mx': x0 + (c/2), 'my': h/2 + rand, 'dy': h*2 + rand}
    phi = math.atan(h/q)
    punktwinkel = (phi-math.pi/4)
    c_sx = q - radius * math.cos(phi)
    c_sy = radius * math.sin(phi)
    c_ex = q + radius * math.sin(phi)
    c_ey = radius * math.cos(phi)
    punkt_x = q + radius/2 * math.sin(punktwinkel)
    punkt_y = radius/2 * math.cos(punktwinkel) 
    rechter_winkel = {'c_sx': c_sx + x0, 'c_sy': c_sy + rand, 'c_ex': c_ex + x0, 'c_ey': c_ey + rand, 'punkt_x': punkt_x + x0, 'punkt_y': punkt_y + rand}        
    parameter.update(rechter_winkel)
    return parameter

def sub_dreiecksseiten(q, h):
    p = (h*h/q)
    c = round(p+q)
    a = round(math.sqrt(h**2+p**2))
    b = round(math.sqrt(h**2+q**2))
    p=round(p)
    return a, b, c, p

def sub_py_tripel(stufe):
    p_zahlen = [[5,4,3,1],[10,8,6,-1],[0.5,0.4,0.3,0.1],[5,3,4,1],[10,6,8,-1],[15,12,9,1],[2.5,2.0,1.5,0.1],[13,12,5,1]]
    if stufe%2 == 1:
        typ2 = random.randint(0,7)
    else:
        typ2 = random.randint(0,4)
    a = p_zahlen[typ2][1]
    b = p_zahlen[typ2][2]
    c = p_zahlen[typ2][0]
    if c < 1:
        einheit = "dm"
    else:
        einheit = "cm"
    str_a,str_b, str_c = (str(x).replace(".",",") for x in (a, b, c))
    scale = 200/c
    p = (a**2/c)
    q = (b**2/c)
    h = math.sqrt(p*q)
    return a, b, c, str_a, str_b, str_c, h, p, q, scale, einheit, p_zahlen[typ2][3]

# Winkel
def sub_segment(center_x, center_y, radius, winkel, id = 0, startwinkel = 90):
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

def sub_winkel_koordinaten(id, center_x, center_y, radius, winkel, startwinkel, color = "None", symbol = "", schenkel = 0, scheitel = False, lire = 1):
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
                text_x = text_x, text_y = text_y, color = color, symbol = symbol, sweepFlag = lire)
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

# Kreis
def sub_kreissegment(scale, x0, Radius, winkel):
    rand = 30
    Radius = Radius * scale
    parameter = {'Radius':Radius, 'winkel': winkel, 'x0': x0,  'y0': Radius + rand, 'mx': x0 +Radius/2, 
                  's_ax': x0 + Radius,                   's_ay': Radius + rand, 
                  's_ex': x0 + Radius *math.cos(winkel), 's_ey': Radius + rand - Radius*math.sin(winkel),
                  'w_ax': x0 + 30,                       'w_ay': Radius + rand, 
                  'w_ex': x0 + 30 *math.cos(winkel),     'w_ey': Radius + rand - 30*math.sin(winkel),
                  'w_mx': x0 + 30 *math.cos(winkel/2),   'w_my': Radius + rand - 30*math.sin(winkel/2)
                  }
    return parameter

def sub_kreisring(scale, Radius, radius,):
    rand = 30
    Radius = Radius * scale
    radius = radius * scale
    parameter = {'Radius': Radius, 'radius': radius, 'x': 200, 'y': 100,
                 'xo': 200 + Radius*math.cos(0.5), 'yo': 100-Radius*math.sin(0.5),
                 'xu': 200 + radius*math.cos(0.5), 'yu': 100+radius*math.sin(0.5)}
    return parameter

def sub_restflaeche(scale, x0, seite, radius,):
    rand = 30
    seite = seite * scale
    radius = radius * scale
    parameter = {'x0': x0, 'y0': rand, 'seite': seite, 'radius': radius, 
                 'x': x0 + seite/2, 'y': rand + seite/2, 
                 'xd_a': x0 +seite/2 - radius, 'xd_e': x0 +seite/2 + radius,
                 'ym': rand + seite}
    return parameter
 
def sub_zylinder(radius, radius_o, hoehe, typ, fuellhoehe = 0):
    masz1 = radius
    masz2 = hoehe
    if hoehe > radius:
        scale = 100/hoehe
    else:
        scale = 100/radius
    radius *= scale
    radius_o *= scale
    hoehe *= scale
    hoehe_2 = hoehe - fuellhoehe * scale
    rand = radius/2 + 100 - hoehe
    parameter = {'typ': typ, 'ox': 200, 'oy': rand, 'ux': 200, 'uy': rand + hoehe,                      # Kreimittelpunkt oben / unten
                'lox': 200 - radius_o, 'loy': rand,  'rox': 200 + radius_o, 'roy': rand,                # Bogen oben links / rechts
                'lux': 200 - radius, 'luy': rand + hoehe, 'rux': 200 + radius, 'ruy': rand + hoehe,     # Bogen unten links / rechts
                'roa': radius_o, 'rob': radius_o/3,                                                     # Durchmesser oben x / y
                'rua': radius, 'rub': radius/3,                                                         # Durchmesser unten x / y
                'my': rand + hoehe/2, 'mx': 200 + (radius+radius_o)/2, 'masz2': masz2}                  # mittlere Hoehe und Beschriftung
    if typ in (17,18):
        parameter['masz1'] = masz1*2
    else:
        parameter['masz1'] = masz1
    if typ == 21:
        fuellstand = {'rlmy': rand + hoehe_2,}                              # Bogen mitte links / rechts}
        parameter['my'] = rand + hoehe - fuellhoehe/2 * scale
        parameter.update(fuellstand)

    return parameter
