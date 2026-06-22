from pathlib import Path
from os import getenv
from dotenv import load_dotenv
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.0/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!

SECRET_KEY = os.getenv("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = getenv("DEBUG", "0") == "1"

# Application definition

ALLOWED_HOSTS = getenv("ALLOWED_HOSTS", "").split(",")
ALLOWED_HOSTS = [h.strip() for h in ALLOWED_HOSTS if h.strip()]
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '.ngrok-free.dev', '*']

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
    'medien',
    'mathetests',
    'duell',
]
#    'register.apps.RegisterConfig'
#LOGIN_URL = '/benutzer/anmelden/'
#LOGOUT_URL = '/benutzer/abmelden/'
#LOGIN_REDIRECT_URL = '/'

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
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
# https://docs.djangoproject.com/en/4.0/ref/settings/#databases

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

# Password validation
# https://docs.djangoproject.com/en/4.0/ref/settings/#auth-password-validators

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


# Internationalization
# https://docs.djangoproject.com/en/4.0/topics/i18n/

LANGUAGE_CODE = 'de-de'

TIME_ZONE = 'Europe/Berlin'

USE_L10N = True

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.0/howto/static-files/



STATIC_URL = "/static/"
if DEBUG:
    STATICFILES_DIRS = [BASE_DIR / "static"]
else:
    # Weg mit dem Umweg über 'staticfiles'
    STATIC_ROOT = "/home/rt/html/static/"

# Default primary key field type
# https://docs.djangoproject.com/en/4.0/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

#CRISPY_TEMPLATE_PACK="bootstrap4"

LOGIN_REDIRECT_URL = "index"
LOGOUT_REDIRECT_URL = "index" 

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



