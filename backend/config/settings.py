from pathlib import Path
import os
from decouple import config

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = config('SECRET_KEY')

DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=lambda v: [h.strip() for h in v.split(',')])

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework',
    'corsheaders',
    'estudiantes',
    'cursos',
    'coordinacion',
    'perfiles',
    'servicios',
    'academico',
    'cuentas',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
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
        'DIRS': [],
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

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': config('DB_NAME', 'plataforma_universitaria'),
        'USER': config('DB_USER', 'admin_user'),
        'PASSWORD': config('DB_PASSWORD', 'admin_password'),
        'HOST': config('DB_HOST', 'db'),
        'PORT': config('DB_PORT', '3306'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-mx'
TIME_ZONE = 'America/Mexico_City'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'

# Adjuntos del contenido de materias. No se publican directamente: se descargan por
# /api/archivos-contenido/<id>/descargar/, que revisa permisos. Con SERVIR_ARCHIVOS_CON_NGINX
# Django solo autoriza y nginx envía el archivo (X-Accel-Redirect), lo que permite adelantar videos.
MEDIA_ROOT = config('MEDIA_ROOT', default=str(BASE_DIR / 'media'))
SERVIR_ARCHIVOS_CON_NGINX = config('SERVIR_ARCHIVOS_CON_NGINX', default=False, cast=bool)
FILE_UPLOAD_PERMISSIONS = 0o644  # nginx (otro contenedor) necesita leerlos
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'cuentas.autenticacion.SesionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_THROTTLE_RATES': {
        'login': '5/min',
    },
    # nginx va delante: tomar la IP del cliente de X-Forwarded-For y no la del proxy,
    # o el límite de intentos de login sería compartido por todos los usuarios
    'NUM_PROXIES': 1,
}

# Sesión por cookie: HttpOnly (JS no puede leerla) y SameSite=Lax por defecto en Django.
# En producción (DEBUG=False) las cookies solo viajan por HTTPS.
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='', cast=lambda v: [o.strip() for o in v.split(',') if o.strip()])

CORS_ALLOWED_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:80",
    "http://localhost:8000",
]
