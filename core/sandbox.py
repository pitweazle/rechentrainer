# from django.shortcuts import render

# def wahrscheinlichkeit():
#     #...
#     titel = "Wahrscheinlichkeitsrechnung"
#     text = "Die Menge aller möglichen Ergebnisse heißt Ergebnisraum.<br>Man bezeichnet ihn mit 'Ω' und setzt die einzlnen Ergebnisse in geschweifte Klammern.<br>"
#     variable = ["irgendeine Aufgabe"]
#     frage = "Ω={"
#     einheit = "}" 
#     #... 
#     return titel, text, frage, einheit, variable

# def main():
#     #...
#     titel, text,  frage, variable, einheit = wahrscheinlichkeit() 
#     text = text.format(*variable)
#     #...
#     context = dict( titel = titel,  text = text, frage = frage, einheit = einheit)
#     return render('core/aufgabe.html', context)

beschriftung = {
                'x_beschriftung': [
                    (n, (n+1)%2*n) for n in range(-2, 3)
                ],
}
print(beschriftung)