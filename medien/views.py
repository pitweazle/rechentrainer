from django.shortcuts import render

def film(req):
    return render(req, 'medien/film.html')  

def installation_film(req):
    return render(req, 'medien/installation_film.html')  

def weitere_aufgaben(req):
    print("hier kommt der Link noch an")
    return render(req, 'medien/weitere_aufgaben.html')  

def weitere_projekte(req):
    return render(req, 'medien/weitere_projekte.html') 

def lernkontrollen(req):
    return render(req, 'medien/lernkontrollen.html')  
    
def download_rechentrainer(req):
    return render(req, 'medien/download_rechentrainer.html')  

def download_lernbox(req):
    return render(req, 'medien/download_lernbox.html')  