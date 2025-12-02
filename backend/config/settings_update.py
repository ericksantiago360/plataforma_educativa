# Agregar esto a backend/config/settings.py

# En INSTALLED_APPS, agregar:
# 'rest_framework',
# 'corsheaders',
# 'estudiantes',
# 'cursos',
# 'coordinacion',

# En MIDDLEWARE, agregar al inicio:
# 'corsheaders.middleware.CorsMiddleware',

# Agregar al final:
REST_FRAMEWORK = {
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 10
}

CORS_ALLOWED_ORIGINS = [
    "http://localhost",
    "http://127.0.0.1",
    "http://localhost:80",
]

import os
from decouple import config

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
