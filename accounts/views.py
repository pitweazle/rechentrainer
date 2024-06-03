from datetime import date, datetime, timedelta, time

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User, Group
from django.contrib import messages
from django.http import HttpResponse, FileResponse, Http404

from django.db.models import Max, Sum, F, Q

from .forms import Register_Form, Profil_Form, Login_Form, Suchen_Form, Loeschen_Form, Zusammen_Form
from .forms import Profil_Aendern_Form, Ort_Form, Lehrer_Aendern_Form, Gruppe_Neu_Form, Gruppe_Aendern_Form, Schueler_Aendern_Form, ProtokollFilter_Gruppe

from .models import Schule, Lerngruppe, Geloescht
from core.models import Zaehler, Profil, Kategorie, Protokoll
 
def name_hj():
    heute = datetime.today()
    jahr = heute.year
    sj = jahr%100*100+jahr%100+1
    if heute.month in range(1,8):
        sj -= 101
    if heute.month in range(2,8):    
        hj = 2
    else:
        hj = 1
    return sj, hj           

def name_next_hj():
    heute = datetime.today()
    jahr = heute.year
    sj = jahr%100*100+jahr%100+1
    if heute.month == 1:
        hj = 2
        sj -=101
    else:
        hj = 1
    if heute.month > 7:
        hj = 2
    return sj, hj      

# Dies ist die Startseite:
def index(req):
    anz_angemeldet = Profil.objects.count()
    anz_lehrer = User.objects.filter(groups__name="Lehrer").count()
    anz_aufg = Protokoll.objects.count()
    lehrer = User.objects.filter(pk=req.user.id, groups__name='Lehrer').exists()
    return render(req, 'index.html', context= {'lehrer': lehrer, 'anz_angemeldet': anz_angemeldet, 'anz_lehrer': anz_lehrer, 'anz_aufg': anz_aufg})

def datenschutz(req):
    return render(req, 'datenschutz.html', context={'titel': "Datenschutz",})

def stimmen(req):
    return render(req, 'stimmen.html', context={'titel': "Stimmen zum Rechentrainer",})

def stufen(req):
    return render(req, 'lehrer/stufen.html', context={'titel': "Was bedeuten die Stufen?",})

# registrieren und anmelden:
def stufe(jg, kurs):
    stufe = 0
    if kurs == "i":
        stufe = 0
    else: 
        if jg < 5:
            stufe = 1
        else:
            if jg > 11:
                jg = 11
                kurs = "Y"
            stufe_liste = [2,4,12,20,26,32,50]
            stufe = stufe_liste[jg-5] 
            if kurs in ["Y","R","E","B"]:
                stufe +=1
    return stufe

def registrieren(req):
    reg_form = Register_Form()
    profil_form = Profil_Form()  
    datenschutz = ""
    if req.method == 'POST':
        neues_halbjahr = req.POST.get('neu', 'nein')
        datenschutz = req.POST.get('datenschutz', 'off')
        reg_form = Register_Form(req.POST)
        profil_form = Profil_Form(req.POST) 
        if datenschutz == "on":
            if  reg_form.is_valid() and profil_form.is_valid(): 
                user = reg_form.save()
                profil = profil_form.save(commit=False)
                kurs = profil_form.cleaned_data['kurs']
                jg = profil_form.cleaned_data['jg']
                profil.stufe = stufe(jg, kurs)
                sj, hj = name_hj()
                profil.sj = sj
                profil.hj = hj
                profil.user = user
                profil.save()
                username = reg_form.cleaned_data['username']
                password = reg_form.cleaned_data['password1']
                user = authenticate(username=username, password=password)
                login(req, user)
                group = Group.objects.get(name='Schüler')
                user.groups.add(group)
                if neues_halbjahr.lower() == 'ja':
                    sj, hj = name_next_hj()            
                    profil.sj = sj
                    profil.hj = hj
                    profil.save()
                if req.POST.get('cookie_loeschen') == 'on':
                    req.session.set_expiry(0)
                return redirect(ort_wahl)
    context = {'reg_form' : reg_form, 'profil_form' : profil_form, 'datenschutz': datenschutz,'titel': "Registrieren"} 
    return render(req, 'registrieren.html', context)

def anmelden(req):
    titel = "Anmelden" 
    if req.method == 'POST':
        #get_expire_at_browser_close()
        form = Login_Form(req.POST)
        if  form.is_valid ():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']            
            user = authenticate(req, username=username, password=password)
            cookie_loeschen = req.POST.get('cookie_loeschen') 
            if cookie_loeschen == 'on':
                req.session.set_expiry(0)
            if user is not None:
                login(req, user)
                return hj_pruefen(req)
        titel = "Username und/oder Passwort stimmen nicht"
    form = Login_Form()
    context = {'form' : form, 'titel': titel} 
    return render(req, 'anmelden.html', context)

def account_loeschen(req):
    try:    
        user = User.objects.get(pk = req.user.id)
    except:
        messages.error(req, "Es ist kein Benutzer angemeldet!!")        
        return render(req, 'index.html')        
    if req.method == 'POST':
        bestaetigt = req.POST.get('bestaetigt', 'off')        
        if bestaetigt == "on":
            logout(req)
            user.delete()
            messages.success(req, "Dein Account und alle deine Daten wurden gelöscht!")
        else:
            messages.error(req, "Löschen wurde abgebrochen!")
        return render(req, 'index.html')
    return render(req, 'admin/account_loeschen.html', context={'titel': "Account löschen",}) 

def hj_pruefen(req):
    if req.user.is_authenticated:
        user = req.user.profil
        heute = datetime.now()
        if heute.month == 1 or heute.month == 7:                            #Frage nach neuem Halbjahr
            next_sj, next_hj = name_next_hj()
            if user.hj == next_hj and user.sj == next_sj:                   #user arbeitet schon am nächsten Hj
                return redirect('uebersicht') 
            else:
                try:
                    if heute.day > user.voreinst.setdefault("frage_hj", 0) and user.voreinst.setdefault("no_hj", False) != True:
                        test = False
                except:
                    user.voreinst["frage_hj"] = 0
                    user.voreinstt["no_hj"] = False
                    user.save()
                if heute.day > user.voreinst.setdefault("frage_hj", 0) and user.voreinst.setdefault("no_hj", False) != True:
                    if heute.month == 1:
                        monat = "Juli"
                        wechsel = "Februar"
                    else:
                        monat = "Januar"
                        wechsel = "August"
                    context = {'monat' : monat, 'wechsel': wechsel}
                    return render(req, 'naechstes_halbjahr.html', context)
            return redirect('uebersicht')  
        else:                                                                   #Überprüfung, ob Halbjahr aktuell ist
            sj, hj = name_hj()
            if user.hj == hj and user.sj == sj:
                pass  
            else:                                                               #falls nicht
                return redirect('neues_halbjahr')  
        return redirect('uebersicht') 
    else:
        return redirect('anmelden')  

def naechstes_halbjahr(req):
    if req.method == 'POST':
        neues_halbjahr = req.POST.get('neu', 'nein')
        keinefragen = req.POST.get('keinefrage') 
        user = get_object_or_404(Profil, user_id = req.user.id)
        if neues_halbjahr.lower() == 'ja':
            for zaehler in Zaehler.objects.filter(user_id = user.id): 
                zaehler.fehler_zaehler = 0  
                zaehler.lsg_zaehler = 0  
                zaehler.hilfe_zaehler = 0  
                zaehler.abbr_zaehler = 0  
                #zaehler.richtig_of = 0
                zaehler.save()
            sj, hj = name_next_hj()
            user.hj = hj
            user.sj = sj
            user.voreinst["no_hj"] = False
            user.voreinst["frage_hj"] = 0
            user.save()
            if user.hj == 2:
                halbjahr = "Halbjahr"
            else:
                halbjahr = "Schuljahr" 
                if user.jg < 13:
                    if str(user.jg) in user.klasse:
                        user.klasse = user.klasse.replace(str(user.jg), str(user.jg+1),1)
                    user.jg +=1
                    neue_stufe = stufe(user.jg, user.kurs)
                    if neue_stufe > user.stufe:
                        user.stufe = neue_stufe
                    user.save()
            return render(req, 'neues_halbjahr.html', context={'halbjahr': halbjahr})
        if keinefragen == "on":
            user.voreinst["no_hj"] = True
            user.voreinst["frage_hj"] = 0
        else:
            user.voreinst["frage_hj"] =  datetime.now().day
        user.save()  
        heute = datetime.now()
        if heute.month == 1 or heute.month == 7: 
            if heute.day > 25:         
                if user.hj == 2:
                    monat = "August"
                else:
                    monat = "Februar" 
                return render(req, 'zweite_frage.html', context={'monat': monat})          
    return redirect('index')

def doch_neues_halbjahr(req):
    user = get_object_or_404(Profil, user_id = req.user.id)
    sj, hj = name_next_hj()
    user.hj = hj
    user.sj = sj
    user.save() 
    if user.hj == 2:
        halbjahr = "Halbjahr"
    else:
        halbjahr = "Schuljahr" 
    return render(req, 'neues_halbjahr.html', context={'halbjahr': halbjahr})   

def neues_halbjahr(req):
    sj, hj = name_hj()
    print(sj,"/",hj)
    user = get_object_or_404(Profil, user_id = req.user.id)
    print(user.sj,"/",user.hj)
    user.voreinst["no_hj"] = False
    user.voreinst["frage_hj"] = 0
    user.hj = hj
    user.sj = sj
    user.save()
    for zaehler in Zaehler.objects.filter(user_id = user.id): 
        zaehler.fehler_zaehler = 0  
        zaehler.lsg_zaehler = 0  
        zaehler.hilfe_zaehler = 0  
        zaehler.abbr_zaehler = 0  
        zaehler.save()
    if user.hj == 2:
        halbjahr = "Halbjahr"
    else:
        halbjahr = "Schuljahr"            
        if user.jg < 13:
            if str(user.jg) in user.klasse:
                user.klasse = user.klasse.replace(str(user.jg), str(user.jg+1),1)
            user.jg +=1
            neue_stufe = stufe(user.jg, user.kurs)
            if neue_stufe > user.stufe:
                user.stufe = neue_stufe
            user.save() 
    return render(req, 'neues_halbjahr.html', context={'halbjahr': halbjahr, "jahrgang": user.jg, "klasse": user.klasse})

#für Schüler
def profil(req):
    print(req.user)
    if User.objects.filter(pk=req.user.id, groups__name='Lehrer').exists():
        print("Lehrer")
        return redirect('profil_lehrer')
    print("Schüler")
    try:
        schueler = get_object_or_404(Profil, user=req.user)
    except:
        return HttpResponse("Zugriff verweigert")        
    profil_form = Profil_Aendern_Form(instance=schueler,)
    if req.method == 'POST':
        details = req.POST.get('details') 
        if details:
            schueler.details = True
        else:
            schueler.details = False
        schueler.save()   
        profil_form = Profil_Aendern_Form(req.POST, instance=schueler)
        if  profil_form.is_valid():
            profil_form.save()
            return redirect('index')
        ort = Ort_Form(req.POST)
        if  ort.is_valid():
            ort_wahl = ort.cleaned_data['ort'] 
            if ort_wahl == None:
                schueler.schule = None
                schueler.gruppe = None
                schueler.save() 
                return render(req, 'schueler/keine_gruppe.html', context={'titel': "en Schulort"})
            schueler.ort=ort_wahl
            schueler.save()
            schulen = Schule.objects.filter(ort_id = ort_wahl)
            return render(req, 'schule_wahl.html', context={'schulen':schulen, 'ort':ort_wahl, 'titel': "Schule wählen"})
    else:
        ort_form = Ort_Form()
        ort_wahl = ""
    context = {'schueler': schueler, 'profil_form': profil_form, 'ort': ort_form, 'titel': "Profil", }
    return render(req, 'schueler/profil.html', context)

# wird nur bei der Registrierung aufgerufen
def ort_wahl(req):
    ort_form = Ort_Form()
    if req.method == 'POST':
        ort_form = Ort_Form(req.POST) 
        if  ort_form.is_valid():
            ort_wahl = ort_form.cleaned_data['ort']
            if ort_wahl == None:
                return render(req, 'schueler/keine_gruppe.html', {'titel': "en Schulort"})
            else:
                user = get_object_or_404(Profil, user = req.user)
                schulen = Schule.objects.filter(ort_id = ort_wahl)
                return render(req, 'schule_wahl.html', context={ 'schulen': schulen, 'titel': "Schule wählen"})
    return render(req, 'ort_wahl.html', context={'ort_form': ort_form, 'titel': "Schulort wählen"})

def schule_wahl(req, schule_id):
    user = get_object_or_404(Profil, user = req.user)
    try:
        schule = get_object_or_404(Schule, id=schule_id)
    except:
        user.schule = None
        user.save()
        return render(req, 'schueler/keine_gruppe.html', {'titel': "en Schulort"})
    lehrer_liste =User.objects.filter(Q(groups__name="Lehrer"), Q(profil__schule = schule_id) | Q(profil__zweite_schule = schule_id))
    user.schule = schule
    user.save()
    if user.klasse.lower() == "lehrer":
        return render(req, 'lehrer/wahl_fertig.html', {'titel': "fertig"})
    else:
        return render(req, 'schueler/lehrer_wahl.html', context={'lehrer_liste': lehrer_liste, 'schule': schule_wahl, 'titel': "Lehrer/in wählen"}) 

def lehrer_wahl(req, lehrer_id):
    try:
        lehrer = get_object_or_404(Profil, user_id = lehrer_id)
        gruppen = Lerngruppe.objects.filter(lehrer = lehrer_id)
    except:
        return render(req, 'schueler/keine_gruppe.html', {'titel': "e Schule"})
    return render(req, 'schueler/gruppe_wahl.html', context={ 'gruppen': gruppen, 'lehrer': lehrer, 'titel': "Lerngruppe wählen"})

def gruppe_wahl(req, gruppe_id):
    schueler = get_object_or_404(Profil, user = req.user)
    try:
        gruppe = get_object_or_404(Lerngruppe, pk = gruppe_id)
        schueler.lerngruppe = gruppe
        schueler.save()
    except:
        return render(req, 'schueler/keine_gruppe.html', context={'titel': "e Gruppe"})
    schueler.gruppe = gruppe
    schueler.save()
    return render(req, 'schueler/gruppe_fertig.html', context={'gruppe': gruppe, 'titel': "fertig!"})

def gruppe_fertig(req, gruppe_id):
    return HttpResponse(gruppe_id)

#für Lehrer
def profil_lehrer(req):
    if User.objects.filter(pk=req.user.id, groups__name='Lehrer').exists():
        lehrer = Profil.objects.get(user=req.user)
        profil_form = Lehrer_Aendern_Form(instance=lehrer,)
        if req.method == 'POST': 
            profil_form = Lehrer_Aendern_Form(req.POST, instance=lehrer)
            if  profil_form.is_valid():
                profil_form.save()
                jg = profil_form.cleaned_data['jg']
                kurs = profil_form.cleaned_data['kurs']
                #lehrer.stufe = stufe(jg, kurs)                       # sorgt dafür, dass Stufe zu Jg und Kurs passt
                lehrer.stufe = profil_form.cleaned_data['stufe']    # mit dieser Zeile kann man die Stufe ohne Vorgaben ändern
                lehrer.save()
                return render(req, 'lehrer/aendern_fertig.html')                            
        context = {'profil_form': profil_form, 'lehrer': lehrer, 'titel': "Profil"}
        return render(req, 'lehrer/profil_lehrer.html', context)
    else:
        return HttpResponse("Zugriff verweigert")

def aufgaben_loeschen(req, lehrer_id):
    if User.objects.filter(pk=req.user.id, groups__name='Lehrer').exists():
        try:
            user = get_object_or_404(Profil, id=lehrer_id)
        except:
            return HttpResponse("Zugriff verweigert")
        if req.method == 'POST':
            bestaetigt = req.POST.get('bestaetigt', 'off')        
            if bestaetigt == "on":
                Zaehler.objects.filter(user=user).delete()
                Protokoll.objects.filter(user=user).delete()                
                return render(req, 'lehrer/aendern_fertig.html', {'titel': "Aufgaben wurden gelöscht"})
                #kategorien = Kategorie.objects.all()
                #return render(req, 'core/uebersicht.html', context={'user': user, 'kategorien': kategorien}) 
            return render(req, 'lehrer/aufgaben_loeschen.html', context={'lehrer': user, 'titel': "wirklich löschen?"}) 
        return render(req, 'lehrer/aufgaben_loeschen.html', context={'lehrer': user,'titel': "Aufgaben löschen",}) 
    else:
        return HttpResponse("Zugriff verweigert")

def meine_gruppen(req):
    if User.objects.filter(pk=req.user.id, groups__name='Lehrer').exists():
        if req.user.is_superuser:
            gruppen = Lerngruppe.objects.all().order_by("lehrer")
            super = True
        else:
            gruppen = Lerngruppe.objects.filter(lehrer=req.user)
            super = None
        return render(req, 'lehrer/meine_gruppen.html', context={'gruppen': gruppen, 'titel': "meine Lerngruppen", 'super': super})
    else:
        return HttpResponse("Zugriff verweigert")

def quote_farbe(richtig, falsch, ungenuegend=1/3):
    try:
        quote = falsch / (richtig + falsch)
        if quote <= 0.1:
            return "gruen"
        elif quote <= ungenuegend:
            return "gelb"
        else:
            return "rot"
    except :
        return None

def protokoll_zeit_filter(protokoll, auswahl):
    sj, hj = name_hj()
    next_sj, next_hj = name_next_hj()
    if auswahl == "next":
        protokoll = protokoll.filter(sj=next_sj, hj=next_hj)  
    elif auswahl == "Halbjahr":
        protokoll = protokoll.filter(sj=sj, hj=hj)                               
    elif auswahl == "heute":
        protokoll = protokoll.filter(start__date = date.today())
    elif auswahl == "Woche":
        protokoll =  protokoll.filter(start__date__gte = date.today() - timedelta(days = 7))
    elif auswahl == "8 Tage":
        protokoll =  protokoll.filter(start__date__gte = date.today() - timedelta(days = 8))    
    elif auswahl == "9 Tage":
        protokoll =  protokoll.filter(start__date__gte = date.today() - timedelta(days = 9))    
    elif auswahl =="Schuljahr":
        protokoll = protokoll.filter(sj = sj) 
    return protokoll

def gruppe_uebersicht(req, gruppe_id):
    from core.views import soll_berechnung, bewertung_kat, bewertung_hj
    sj, hj = name_hj()
    gruppe = get_object_or_404(Lerngruppe, pk=gruppe_id)
    jg = gruppe.jg
    aufgaben_pro_woche = gruppe.aufgaben_pro_woche
    if aufgaben_pro_woche < 1:
        aufgaben_pro_woche = 10 * jg
    wahl = "aktuelles Halbjahr"
    form_filter = ProtokollFilter_Gruppe
    if gruppe.lehrer != req.user and not req.user.is_superuser:
        return HttpResponse("Zugriff verweigert")
    titel = f"{gruppe.name}, {gruppe.lehrer.profil.vorname} {gruppe.lehrer.profil.nachname}"
    gesamtzeit_text = ""
    if gruppe.name != "keine Gruppe":
        protokoll = Protokoll.objects.filter(user__gruppe = gruppe)               # alle Protokollobjekte der Gruppe
    else:
        protokoll = Protokoll.objects.filter(user__gruppe = None)                 # alle Protokollobjekte der Schülerinnen und Schüler ohne Gruppenzugehörigkeit
        #protokoll = protokoll.exclude(user__user__groups__name = 'Lehrer')
        #protokoll = protokoll.exclude(user__klasse = "Lehrer")
    if req.method == 'POST':
        auswahl = form_filter(req.POST)
        filter = auswahl.fields['auswahl'].choices
        auswahl_liste = dict(filter)
        if auswahl.is_valid(): 
            auswahl = auswahl.cleaned_data['auswahl']
            protokoll = protokoll_zeit_filter(protokoll, auswahl)
            wahl = auswahl_liste[auswahl]
    else:
        wahl = "aktuelles Halbjahr"
        protokoll = protokoll.filter(sj=sj, hj=hj)
    startdatum = gruppe.erstellt_am
    schulwoche, woche_halbjahr, soll_hj, soll_kat, pflicht_kat = soll_berechnung(sj, hj, jg, aufgaben_pro_woche, startdatum)                    # berechnet den Aufgabensoll für das Halbjahr
    prozent_summe = 0
    prozent_summe_farbe = False
    temp = protokoll.aggregate(Sum('richtig'))['richtig__sum']
    richtig_gesamt = temp if temp else  0
    falsch_gesamt = 0
    katmax_max = protokoll.aggregate(Max('kategorie__zeile'))['kategorie__zeile__max']
    note_anzeigen = True if wahl == "aktuelles Halbjahr" else False
    if not katmax_max:
        kategorien = []
        summen = []
        aufgaben_der_schueler = []
        kategorie_summen = [(0, "-")]
        gesamtzeit_text = "-"
        katmax_max = 0
    if 1 == 1:
        kategorien = list(Kategorie.objects.filter(zeile__lt=katmax_max + 1))
        kategorie_summen = [(0, "-")] * (katmax_max+1) 
        kategorie_fehler = [(0)] * (katmax_max+1) 
        gesamtzeit = timedelta()
        if gruppe.name != "keine Gruppe":
            schueler_liste = Profil.objects.filter(gruppe__name=gruppe.name).order_by("user__profil__vorname") 
        else:
            schueler_liste = Profil.objects.filter(gruppe=None).order_by("user__profil__vorname") 
        aufgaben_der_schueler = []
        for user in schueler_liste:
            hj_stimmt = user.sj == sj and user.hj == hj
            richtig_sum = 0
            protokoll_user = protokoll.filter(user = user)                  # die Gesamtsummen der einzelnen User
            summen = (
            protokoll_user
            .values("user")
            .annotate(richtig_sum=Sum('richtig'))
            .annotate(zeit_sum=Sum(F('end') - F('start')))
            ) 
            dauer_text = "0:00"
            for g in summen:
                richtig_sum = g['richtig_sum']
                dauer = g['zeit_sum']
                try:
                    seconds = int(dauer.total_seconds())
                    mm = int(seconds/60)
                    hh, mm = divmod(mm, 60)
                    dauer_text = f"{hh}:{mm:02d}" 
                    gesamtzeit = gesamtzeit + dauer
                except:
                    dauer_text = "---"
            aufgaben = [(0, "-")] * (katmax_max+1)
            kategorie_werte = (                                                     # die Summen der einzelnen Kategoren des jeweiligen Users
                protokoll_user
                .values("kategorie__zeile")
                .annotate(richtig_sum=Sum('richtig'))
                #.annotate(falsch_sum=Sum('falsch'))
                )
            falsch_sum = 0
            for k in kategorie_werte:
                index = int(k['kategorie__zeile'])
                richtig_kat = k['richtig_sum']
                #falsch_kat = k['falsch_sum']
                kat_name = Kategorie.objects.get(zeile = index)
                falsch_kat = lsg_kat = abbr_kat = 0
                zaehler = Zaehler.objects.filter(user = user, kategorie = kat_name)
                if zaehler.count()== 0:
                    fehler, created = Geloescht.objects.get_or_create(user = user.user)
                    if created:
                        fehler.text = "folgende Zählerobjekte wurden angelegt: "
                        fehler.text += str(kat_name)+ ", "
                    else:
                        fehler.text += str(kat_name)+ ", "
                    fehler.save()
                else:
                    zaehler = zaehler.first()
                    falsch_kat = zaehler.fehler_zaehler
                    lsg_kat = zaehler.lsg_zaehler
                    abbr_kat = zaehler.abbr_zaehler
                    # if zaehler.first().fehler_zaehler < falsch_kat:
                    #     falsch_kat = zaehler.first().fehler_zaehler
                falsch_sum += falsch_kat
                kategorie_fehler[index] += falsch_kat
                quote = quote_farbe(richtig_kat, falsch_kat)
                aufgaben[index] = (quote, richtig_kat)
                prozent_kat, prozent_kat = bewertung_kat(soll_kat, richtig_kat, falsch_kat, lsg_kat, abbr_kat, user.stufe)      # berechnet die Wertung der Kategorie
                prozent_summe += prozent_kat
            prozent_summe_farbe, prozent_summe, note = bewertung_hj(prozent_summe, pflicht_kat, user.stufe)                         # Berechnung der Gesamtnote
            if soll_hj < 10*pflicht_kat and prozent_summe < 50:
                note = "-"
                prozent_summe_farbe = None
            quote_sum = quote_farbe(richtig_sum, falsch_sum)
            aufgaben[0] = (quote_sum, int(richtig_sum))
            aufgaben_der_schueler.append((
                user, hj_stimmt, prozent_summe_farbe, prozent_summe, note, dauer_text, aufgaben
            ))
            seconds = int(gesamtzeit.total_seconds())
            mm = int(seconds/60)
            hh, mm = divmod(mm, 60)
            gesamtzeit_text = f"{hh}:{mm:02d}" 
            falsch_gesamt += falsch_sum
        gesamtsummen = (
            protokoll                                                           # hier werden die Gesamtsummen der einzelnen Kategorien bestimmt
            .values("kategorie__zeile")
            .annotate(richtig_sum=Sum('richtig'))
            .annotate(zeit_sum=Sum(F('end') - F('start')))
            )  
        for k in gesamtsummen: 
            index = int(k['kategorie__zeile'])
            richtig_sum = k['richtig_sum']
            quote = quote_farbe(richtig_sum, kategorie_fehler[index])
            kategorie_summen[index] = (quote, richtig_sum)
    quote_sum = quote_farbe(richtig_gesamt, falsch_gesamt)                      # die Gesamtsumme und deren Farbe
    kategorie_summen[0] = (quote_sum, int(richtig_gesamt))
    context={'gruppe_id': gruppe_id,  'wahl': wahl, 'form_filter': form_filter, 'wahl': wahl,
        'aufgaben_der_schueler':aufgaben_der_schueler, 'kategorien': kategorien, 'titel': titel, 'summen': kategorie_summen, 'gesamtzeit': gesamtzeit_text, 'note_anzeigen': note_anzeigen}  
    return render(req, 'lehrer/gruppe_uebersicht.html', context)

def neue_gruppe(req):
    if User.objects.filter(pk=req.user.id, groups__name='Lehrer').exists():
        gruppe_neu = Gruppe_Neu_Form() 
        if req.method == 'POST':
            gruppe_form = Gruppe_Neu_Form(req.POST) 
            if  gruppe_form.is_valid():
                #lehrer = req.user
                #gruppe_form.save()
                gruppen = Lerngruppe.objects.filter(lehrer=req.user).order_by('name')
                neu = gruppe_form.cleaned_data['name']
                jg = gruppe_form.cleaned_data['jg']
                aufgaben = gruppe_form.cleaned_data['aufgaben_pro_woche']
                gruppe, created = Lerngruppe.objects.get_or_create(name = neu, lehrer = req.user, jg = jg, aufgaben_pro_woche = aufgaben)
                if not created:
                    return render(req, 'lehrer/neue_gruppe.html', context={'gruppe': gruppe_form, 'titel': "Ein Gruppe mit diesem Name existiert schon!",})                 
                return render(req, 'lehrer/meine_gruppen.html', context={'gruppen': gruppen, 'titel': "neue Lerngruppe wurde angelegt"}) 
        return render(req, 'lehrer/neue_gruppe.html', context={'gruppe_neu': gruppe_neu, 'titel': "neue Lerngruppe anlegen",})
    else:
        return HttpResponse("Zugriff verweigert")

def gruppe_aendern(req, gruppe_id):
    gruppe = get_object_or_404(Lerngruppe, pk=gruppe_id)
    if gruppe.lehrer != req.user:
        return HttpResponse("Zugriff verweigert")
    if req.method == 'POST':
        gruppe_form = Gruppe_Aendern_Form(req.POST, instance=gruppe)
        if gruppe_form.is_valid():
            gruppe_form.save()
            gruppen = Lerngruppe.objects.filter(lehrer=req.user)
            return render(req, 'lehrer/meine_gruppen.html', context={'gruppen': gruppen,'titel': "Daten wurden geändert"}) 
        else:
            return HttpResponse("Entschuldigung, das hat nicht geklappt!")
    else:
        gruppe_form = Gruppe_Aendern_Form(instance=gruppe,)
        context={'gruppe_form': gruppe_form, 'gruppe': gruppe, 'titel': "Daten der Lerngruppe ändern",}
        return render(req, 'lehrer/gruppe_aendern.html', context) 

def gruppe_loeschen(req, gruppe_id):
    gruppe = Lerngruppe.objects.get(pk = gruppe_id)
    if gruppe.lehrer != req.user:
        return HttpResponse("Zugriff verweigert")
    if req.method == 'POST':
        bestaetigt = req.POST.get('bestaetigt', 'off')        
        if bestaetigt == "on":
            gruppe.delete()
            gruppen = Lerngruppe.objects.filter(lehrer=req.user)
            return render(req, 'lehrer/meine_gruppen.html', context={'gruppen': gruppen, 'titel': "Gruppe wurde gelöscht!"}) 
        return render(req, 'lehrer/gruppe_loeschen.html', context={'gruppe': gruppe, 'titel': "wirklich löschen?"}) 
    return render(req, 'lehrer/gruppe_loeschen.html', context={'gruppe': gruppe, 'titel': "Gruppe löschen",}) 

def mein_schueler(req, schueler_id, hj_stimmt):
    mein_schueler = get_object_or_404(Profil, id=schueler_id)
    if not req.user.is_superuser:
        if mein_schueler.gruppe.lehrer != req.user: 
            return HttpResponse("Zugriff verweigert")
    try:
        gruppe = mein_schueler.gruppe
        titel = str(gruppe.name) + ": " + str(mein_schueler)
    except:
        gruppe = get_object_or_404(Lerngruppe, name = "keine Gruppe")
        titel = str(mein_schueler) + " keine Gruppe"
    context={'titel': titel,'schueler': mein_schueler, 'gruppe': gruppe, 'aktuelles_hj': hj_stimmt}
    return render(req, 'lehrer/mein_schueler.html', context) 

def schueler_aendern(req, schueler_id):
    schueler = Profil.objects.get(id=schueler_id)
    if schueler.gruppe.lehrer != req.user:
        return HttpResponse("Zugriff verweigert")
    if req.method == 'POST': 
        profil_form = Schueler_Aendern_Form(req.POST, instance=schueler)
        if  profil_form.is_valid():
            profil_form.save()
            jg = profil_form.cleaned_data['jg']
            kurs = profil_form.cleaned_data['kurs']
            schueler.stufe = stufe(jg, kurs)
            schueler.save() 
            return render(req, 'lehrer/aendern_fertig.html', {'titel': "Daten wurden geändert"})
        else:
            return HttpResponse("Entschuldigung, das hat nicht geklappt!")
    profil_form = Schueler_Aendern_Form(instance=schueler,)
    context = {'profil_form': profil_form, 'schueler': schueler, 'titel': "Schülerdaten ändern"}
    return render(req, 'lehrer/schueler_aendern.html', context)

# Hier unten sind einige Routinen, die direkt aus dem Browser aufgerufen werden 
def karteileichen(req):
    if not req.user.is_superuser:
        return HttpResponse("Zugriff verweigert")
    auswahl = Profil.objects.filter(user__date_joined__lt=date(2023,8,1))
    print("Teil: ",auswahl.count())    
    for a in auswahl:
        if a.jg < 13:
            if str(a.jg) in a.klasse:
                print(a.klasse)
                a.klasse = a.klasse.replace(str(a.jg), str(a.jg+1),1)
            a.jg +=1
            try:
                neue_stufe = stufe(a.jg, a.kurs)
                if neue_stufe > a.stufe:
                    a.stufe = neue_stufe
                print(a, "neuer_Jg: ", a.jg, ", Stufe: ", a.stufe, "neue Stufe: ",  neue_stufe,)
            except:
                print(a)
    return HttpResponse("fertig!")

def loeschen_alt(req):
    if not req.user.is_superuser:
        return HttpResponse("Zugriff verweigert")
    #auswahl = User.objects.filter(date_joined__lt=date(2023,8,1), date_joined = last_login)
    auswahl = User.objects.filter(date_joined__lt=date(2023,8,1))
    print("Anzahl: ",auswahl.count())
    n=0   
    for a in auswahl:
        if (a.date_joined.date() ) == ((a.last_login.date() )):
            try:
                user = Profil.objects.get(pk = a.id)
                aufgaben = Protokoll.objects.filter(user_id = a.id).count()
                print(user, " Augaben: ", aufgaben)
                if aufgaben == 0:
                    print("keine Aufgaben - Account gelöscht: ", a)
                    #a.delete()
            except:
                print("kein Profil - Account gelöscht: ",a)
                #a.delete()
    return HttpResponse("fertig!")

def suchen(req, gruppe_id=None):
    if User.objects.filter(pk=req.user.id, groups__name='Lehrer').exists() or req.user.is_superuser:
        #suchen_form = Suchen_Form
        loeschen_form = Loeschen_Form
        zusammen_form = Zusammen_Form
        vorname = nachname = nachricht = ""
        if not gruppe_id: 
            profile = Profil.objects.filter(gruppe = None).order_by('vorname','nachname')
            profile = profile.filter(~Q(user__groups__name = 'Lehrer'))
        else:
            gruppe = Lerngruppe.objects.get(id = gruppe_id)
            if gruppe.name == "keine Gruppe" or gruppe_id == None:
                profile = Profil.objects.filter(gruppe = None).order_by('vorname','nachname')
                profile = profile.filter(~Q(user__groups__name = 'Lehrer'))
            else:
                profile = Profil.objects.filter(gruppe_id = gruppe_id).order_by('vorname','nachname')
        zeilen = []    
        if req.method == "POST":
            zusammen_form = Zusammen_Form(req.POST)
            if zusammen_form.is_valid():
                quelle = zusammen_form.cleaned_data['quelle']
                ziel = zusammen_form.cleaned_data['ziel']
                #try: 
                if ziel  and quelle :
                    profil_id_ziel = User.objects.get(id = ziel).id 
                    profil_ziel = Profil.objects.get(user_id = profil_id_ziel)
                    gruppe = profil_ziel.gruppe
                    if gruppe:
                        gruppe_id = gruppe.id
                    vorname = profil_ziel.vorname 
                    nachname = profil_ziel.nachname 
                    profil_id_quelle = User.objects.get(id = quelle).id 
                    profil_quelle = Profil.objects.get(user_id = profil_id_quelle)
                    vorname_quelle = profil_quelle.vorname 
                    nachname_quelle = profil_quelle.nachname
                    if  not req.user.is_superuser and (vorname_quelle.upper() != vorname.upper() or nachname_quelle.upper() != nachname.upper()):  
                        nachricht = "Namen stimmen nicht überein!"
                    else:
                        protokolle = Protokoll.objects.filter(user = profil_quelle)
                        if protokolle.count() == 0:
                            nachricht = "Es sind keine Aufgaben zum Übertragen da."
                        else:
                            user = User.objects.get(id = profil_quelle.user.id)
                            verschoben, created = Geloescht.objects.get_or_create(user = user)
                            heute = date.today()
                            zaehler_quelle = Zaehler.objects.filter(user = profil_quelle)
                            nachricht = "Der/die Zähler: "
                            for q in zaehler_quelle:
                                ziele = Zaehler.objects.filter(user = profil_ziel, kategorie = q.kategorie)
                                if ziele.count() == 0:
                                    nachricht = nachricht + '"' + str(q.kategorie) + '", '
                                    q.user = profil_ziel
                                    q.save()
                                else:
                                    ziel = ziele.first()
                                    if  ziel.sj >0 and ziel.sj == q.sj and ziel.hj == q.hj:
                                        ziel.fehler_zaehler += q.fehler_zaehler
                                        ziel.abbr_zaehler += q.abbr_zaehler
                                        ziel.lsg_zaehler += q.lsg_zaehler
                                        ziel.hilfe_zaehler += q.hilfe_zaehler
                                        if ziel.richtig_of < q.richtig_of:
                                            ziel.richtig_of = q.richtig_of
                                        if ziel.letzte < q.letzte:
                                            ziel.letzte = q.letzte
                                        ziel.save()
                            if nachricht != "Der/die Zähler: ":
                                nachricht += ' wurde(n) am {} von Account "{}" übernommen.<br>'.format(heute, profil_quelle.user)
                                verschoben.text += nachricht
                                verschoben.save()                            
                            n = 0
                            for protokoll in protokolle:
                                n +=1
                                protokoll.user = profil_ziel
                                protokoll.anmerkung = "übertragen von user ID: ", quelle
                                protokoll.save()
                            nachricht = 'am {} wurden {} Aufgaben von Account "{}" auf Account "{}" übertragen.'.format(heute, n, profil_quelle.user,profil_ziel.user)
                            verschoben.text += nachricht
                            verschoben.save()                            
                    profile = Profil.objects.filter(gruppe_id = gruppe_id).order_by('vorname','nachname')
            loeschen_form = Loeschen_Form(req.POST)
            if loeschen_form.is_valid():
                try:
                    loeschen = loeschen_form.cleaned_data['loeschen']
                    if loeschen:
                        try:
                            user = User.objects.get(id = loeschen)
                            gruppe = user.profil.gruppe
                            if gruppe:
                                gruppe_id = gruppe.id
                        except:
                            nachricht = "Ein Account mit der ID {} existiert nicht".format(loeschen)
                            context = {"loeschen_form": loeschen_form, "zusammen_form": zusammen_form, "zeilen" : zeilen, "nachricht": nachricht}
                            render(req, 'admin/suchen.html', context)
                        try:
                            profil = Profil.objects.get(user__id = user.id)
                        except:
                            user.groups.clear()
                            group = Group.objects.get(name='Gelöscht')
                            user.groups.add(group)
                            nachricht = 'Zu dem Account "{}" mit der ID "{}" existiert kein Userprofil'.format(user, loeschen)
                            context = {"loeschen_form": loeschen_form, "zusammen_form": zusammen_form, "zeilen" : zeilen, "nachricht": nachricht}
                            return render(req, 'admin/suchen.html', context)
                        if not req.user.is_superuser and profil.gruppe.lehrer !=  (req.user): 
                            nachricht = " Der user {} ist nicht Ihrer Lerngruppe zugeordnet".format(profil.user)
                        else: 
                            protokolle = Protokoll.objects.filter(user = profil)                 
                            if protokolle.count() > 0 and not req.user.is_superuser:
                                nachricht = 'Mit dem Account "{}" ID:{} wurden schon {} Aufgaben gerechnet, die müssen zuerst übertragen werden!'.format(user, loeschen,protokolle.count())
                            else:
                                heute = date.today()
                                nachricht = 'Das Userprofil "{}" mit dem Account "{}" wurde am {} von {} {} gelöscht.'.format(profil, user, heute, req.user.profil.vorname, req.user.profil.nachname)
                                user.groups.clear()
                                group = Group.objects.get(name='Gelöscht')
                                user.groups.add(group)
                                profil.delete()
                                geloescht, created = Geloescht.objects.get_or_create(user = user)
                                geloescht.text += nachricht
                                geloescht.save()
                            profile = Profil.objects.filter(gruppe_id = gruppe_id).order_by('vorname','nachname')
                except:
                    nachricht = "Mit der letzten Eingabe stimmt was nicht!"        
                    render(req, 'admin/suchen.html')
        sj, hj = name_hj()
        for profil in profile:
            gesamt = Protokoll.objects.filter(user_id = profil.id)
            neu = gesamt.filter(sj = sj, hj = hj)
            zeilen.append((profil, gesamt.count, neu.count))
        context = {"loeschen_form": loeschen_form, "zusammen_form": zusammen_form, "zeilen" : zeilen, "nachricht": nachricht, 'titel': "Accounts löschen"}
        return render(req, 'admin/suchen.html', context)
    else:
        return HttpResponse("Zugriff verweigert")

def reparatur(req, id):
    if not req.user.is_superuser:
        return HttpResponse("Zugriff verweigert")
    protokoll = Protokoll.objects.filter(user__id = id,start__gt=date(2024,2,1))
    print(protokoll.first().user)
    print("Anzahl: ",protokoll.count())    
    for a in protokoll:
        a.hj = 2 
        a.save()      
    return HttpResponse("fertig!")    