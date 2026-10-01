import os
import socket
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# 2. .env laden (Muss im gleichen Ordner wie manage.py liegen)
load_dotenv(BASE_DIR / ".env")

# 3. Sicherheit (Werte kommen aus der .env)
SECRET_KEY = os.getenv("SECRET_KEY")
DEBUG = os.getenv("DEBUG", "False") == "True"

USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Erlaubte Hosts als Liste (in .env mit Komma getrennt)
ALLOWED_HOSTS = ['physiktrainer.app','www.physiktrainer.app','rt.uber.space','127.0.0.1','localhost']

CSRF_TRUSTED_ORIGINS = ['https://physiktrainer.app', 'https://www.physiktrainer.app']

# 4. Weiche für Uberspace-Erkennung
ON_UBERSPACE = 'caelum' in socket.gethostname()

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'physik',  # Deine App
]

MIDDLEWARE = [
    'physik.middleware.BasicAuthMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [ BASE_DIR / "templates" ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# 5. Datenbank (Immer SQLite für den Physiktrainer im PT-Ordner)
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# 6. Internationalisierung
LANGUAGE_CODE = "de"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

# 7. Static & Media (Saubere Struktur für PT und RT gemeinsam)
STATIC_URL = '/static/'

if ON_UBERSPACE:
    # Jetzt direkt in den echten html-Ordner (ohne 'staticfiles' Umweg)
    STATIC_ROOT = '/home/rt/html/static/'
    
    # Der neue zentrale Ort für alle Bilder
    MEDIA_ROOT = '/home/rt/html/media/'
else:
    # Lokal auf Windows bleibt alles beim Alten
    STATIC_ROOT = BASE_DIR / "staticfiles" 
    MEDIA_ROOT = BASE_DIR / "media"

MEDIA_URL = "/media/"
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Deine zusätzlichen Einstellungen
LOGOUT_ON_GET = True
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# settings.py auf dem Server
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.artfiles.de'
EMAIL_PORT = 587
EMAIL_USE_TLS = True

# Diese Daten kommen aus deiner .env
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER") # info@physiktrainer.app
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")

DEFAULT_FROM_EMAIL = 'info@physiktrainer.app'
SERVER_EMAIL = 'info@physiktrainer.app'