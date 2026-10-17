from django.test import TestCase
import random
from collections import defaultdict
from django.test import SimpleTestCase
from core.views import dreiecke


class DreieckeTest(SimpleTestCase):

    def test_alle_typen_stuerzen_nicht_ab(self):
        fehler = defaultdict(int)
        for typ in range(1, 28):
            for stufe in (1, 2, 3, 4):
                for _ in range(100):
                    try:
                        ergebnis = dreiecke(
                            jg=8, stufe=stufe, aufgnr=1,
                            typ_anf=typ, typ_end=typ,
                            reihenfolge=None, optionen="",
                        )
                        self.assertEqual(len(ergebnis), 13)
                    except Exception as e:
                        fehler[(typ, type(e).__name__, str(e)[:60])] += 1
        if fehler:
            meldung = "\n".join(
                f"Typ {t}: {n}x {name}: {text}"
                for (t, name, text), n in sorted(fehler.items())
            )
            self.fail("Abstürze:\n" + meldung)

    def test_winkelaufgaben_fragen_nach_winkel(self):
        for typ in (25, 26, 27):
            for _ in range(100):
                ergebnis = dreiecke(
                    jg=8, stufe=3, aufgnr=1,
                    typ_anf=typ, typ_end=typ, reihenfolge=None,
                )
                text = ergebnis[3]
                self.assertNotIn("Seite", text, f"Typ {typ}: {text}")