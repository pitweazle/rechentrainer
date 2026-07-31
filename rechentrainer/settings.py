from pathlib import Path
from os import getenv
import socket
from dotenv import load_dotenv
import os

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

# Weiche für Uberspace-Erkennung
ON_UBERSPACE = 'caelum' in socket.gethostname()

# Static & Media (Saubere Struktur für PT und RT gemeinsam)
STATIC_URL = '/static/'
MEDIA_URL = '/media/'

if ON_UBERSPACE:
    # Jetzt direkt in den echten html-Ordner (ohne 'staticfiles' Umweg)
    # STATIC_ROOT = '/home/rt/html/static/'
    # MEDIA_ROOT = '/home/rt/html/media/'
    STATIC_ROOT = '/var/www/virtual/rt/html/static/'
    MEDIA_ROOT = '/var/www/virtual/rt/html/media/'

else:
    # Lokal auf Windows bleibt alles beim Alten
    STATIC_ROOT = BASE_DIR / "staticfiles" 
    MEDIA_ROOT = BASE_DIR / "media"
    
    # WICHTIG für lokal, damit zentrale statische Dateien gefunden werden:
    STATICFILES_DIRS = [
        BASE_DIR / "static",
    ]

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

SECRET_KEY = os.getenv("SECRET_KEY")

DEBUG = getenv("DEBUG", "0") == "1"

# Application definition
ALLOWED_HOSTS = getenv("ALLOWED_HOSTS", "").split(",")
ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS if h.strip()]

CSRF_TRUSTED_ORIGINS = getenv("CSRF_TRUSTED_ORIGINS", "").split(",")
CSRF_TRUSTED_ORIGINS = [o.strip() for o in CSRF_TRUSTED_ORIGINS if o.strip()]

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',    
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'accounts',
    'core', 
    'physik',
    'medien',
    'mathetests',
    'duell',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'accounts.middleware.PlatformSwitchMiddleware',
]

ROOT_URLCONF = 'rechentrainer.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [
            BASE_DIR / "templates"
        ],
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

WSGI_APPLICATION = 'rechentrainer.wsgi.application'

# Database
DB_ENGINE = getenv("DB_ENGINE", "django.db.backends.sqlite3")

if DB_ENGINE == "django.db.backends.sqlite3":
    DATABASES = {
        "default": {
            "ENGINE": DB_ENGINE,
            "NAME": getenv("DB_NAME", BASE_DIR / "db.sqlite3"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": DB_ENGINE,
            "NAME": getenv("DB_NAME"),
            "USER": getenv("DB_USER"),
            "PASSWORD": getenv("DB_PASSWORD"),
            "HOST": getenv("DB_HOST", "localhost"),
            "PORT": getenv("DB_PORT", "5432"),
            'OPTIONS': {
                'client_encoding': 'UTF8',
            }
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


LANGUAGE_CODE = 'de-de'

TIME_ZONE = 'Europe/Berlin'

USE_L10N = True

USE_I18N = True

USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


ADMINS = [("Rechentrainer", "info@rechentrainer.app"),]
MANAGERS = ADMINS
DEFAULT_FROM_EMAIL = "info@rechentrainer.app"
SERVER_EMAIL = "info@rechentrainer.app"

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'  # SMTP-Backend
EMAIL_HOST = 'smtp.dcpserver.de'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'info@rechentrainer.app'

EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD")  # aus .env
DEFAULT_FROM_EMAIL = 'info@rechentrainer.app'
SERVER_EMAIL = 'info@rechentrainer.app'  # für Error-Mails

#SVG_DIRS=[os.path.join(BASE_DIR, 'my-svgs')]

#SESSION_COOKIE_AGE = 120 #das wären zwei Minuten
#SESSION_EXPIRE_AT_BROWSER_CLOSE = True



