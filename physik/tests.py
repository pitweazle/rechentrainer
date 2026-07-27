from django.contrib.auth.models import AnonymousUser # Falls der User egal ist

from django.test import TestCase
from physik.models import ThemenBereich, Kapitel, Aufgabe, AufgabeOption
from physik.bewertung import bewerte_aufgabe
from django.test import RequestFactory

class SchlagwortLogikTest(TestCase):

    def setUp(self):
        # WICHTIG: Das "self." vor thema und kapitel
        self.thema = ThemenBereich.objects.create(ordnung=1, thema="Wärmelehre", farbe="red", kurz="W")
        self.kapitel = Kapitel.objects.create(thema=self.thema, zeile=1, kapitel="Wärmeausbreitung")

    def test_typ1_exakt(self):
        factory = RequestFactory()
        request_dummy = factory.get('/') # Erstellt einen leeren Test-Request
        request_dummy.user = AnonymousUser()  # Oder ein echter Test-User        """Prüft Typ 1: Muss exakt übereinstimmen"""
        # Wir nutzen thema/kapitel aus dem setUp (self.thema / self.kapitel)
        aufgabe_t1 = Aufgabe.objects.create(
            lfd_nr="T001", 
            thema=self.thema, 
            kapitel=self.kapitel,
            typ="1", 
            loesung="Thermometer"
        )
        
        # 1. Das aufgabe-Objekt, 2. Die Antwort des Users
        res = bewerte_aufgabe(
            aufgabe=aufgabe_t1, 
            user_antwort="Thermometer", 
            request=request_dummy,
            session={}
            
            )
        self.assertTrue(res.get("richtig"), "Typ 1: 'Thermometer' sollte richtig sein.")

    def test_typ101_fuzzy(self):
        factory = RequestFactory()
        request_dummy = factory.get('/') # Erstellt einen leeren Test-Request   
        request_dummy.user = AnonymousUser() 
        """Prüft Typ 101: Sollte Tippfehler verzeihen"""
        aufgabe_t101 = Aufgabe.objects.create(
            lfd_nr="T101", 
            thema=self.thema, 
            kapitel=self.kapitel,
            typ="1o1", 
            loesung="Thermometer"
        )

        # Auch hier: Erst aufgabe, dann die (falsch geschriebene) loesung
        res = bewerte_aufgabe(
            aufgabe=aufgabe_t101, 
            user_antwort="Termometer", 
            request=request_dummy,
            session={}
            )
        self.assertTrue(
            res.get("richtig"), 
            "Typ 1o1: 'Termometer' sollte per Fuzzy-Matching erkannt werden."
        )

    def test_typ1X_casesensitv(self):
        factory = RequestFactory()
        request_dummy = factory.get('/') # Erstellt einen leeren Test-Request   
        request_dummy.user = AnonymousUser() 
        """Prüft Typ 1X: Sollte Kleinschreibung akkzeptieren"""
        aufgabe_t1X = Aufgabe.objects.create(
            lfd_nr="T1X", 
            thema=self.thema, 
            kapitel=self.kapitel,
            typ="1X", 
            loesung="Thermometer"
        )

        # Auch hier: Erst aufgabe, dann die (falsch geschriebene) loesung
        res = bewerte_aufgabe(
            aufgabe=aufgabe_t1X, 
            user_antwort="thermometer", 
            request=request_dummy,
            session={}
            )
        self.assertTrue(
            res.get("richtig"), 
            "Typ 1X: 'Thermometer' sollte Kleinschreibung akkzeptieren."
        )

    def test_typ1Z_fuzzy_locker(self):
        factory = RequestFactory()
        request_dummy = factory.get('/') # Erstellt einen leeren Test-Request   
        request_dummy.user = AnonymousUser() 
        """Prüft Typ 1Z: Sollte termomter akkzeptieren"""
        aufgabe_t1Z = Aufgabe.objects.create(
            lfd_nr="T1Z", 
            thema=self.thema, 
            kapitel=self.kapitel,
            typ="1Z", 
            loesung="Thermometer"
        )

        # Auch hier: Erst aufgabe, dann die (falsch geschriebene) Antwort
        res = bewerte_aufgabe(
            aufgabe=aufgabe_t1Z, 
            user_antwort="termomter", 
            request=request_dummy,
            session={}
            )
        self.assertTrue(
            res.get("richtig"), 
            "Typ 1Z: 'Thermometer' sollte 'termomter'' akkzeptieren."
        )