# -*- coding: utf-8 -*-
"""
Django settings for myproject project.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/1.8/ref/settings/
"""

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
import random
chars = 'abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)'
SECRET_KEY = "".join([random.SystemRandom().choice(chars) for n in range(50)])

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['127.0.0.1', 'localhost']

# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    # internal apps
    'mafiaapp.apps.MafiaAppConfig',
    'identicon.apps.IdenticonConfig',
    # third party
    # 'silk',
    'rest_framework',
    'corsheaders',
    'django_summernote',
    # 'djangosecure',
    # 'sslserver',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # third party
    # 'silk.middleware.SilkyMiddleware',
    # internal middleware
    #'mafiaapp.middleware.CustomLogger',
    'visitor_activity.apps.VisitorActivityConfig',

)

CORS_ORIGIN_ALLOW_ALL = True
ROOT_URLCONF = 'mafpub.urls'

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

#CUSTOM_LOGGER_FILENAME = os.path.join(BASE_DIR, 'user_activity.log')
USER_ACTIVITY_LOG_FILENAME = os.path.join(BASE_DIR, 'visitor_activity.log')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'print_file': {
            'format': '%(asctime)s %(message)s',
            'datefmt': '%H:%M:%S',
        },
    },
    'handlers': {
        'file': {
            'level': 'DEBUG',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'debug.log'),
        },
        'print_file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': os.path.join(BASE_DIR, 'print.log'),
            'formatter': 'print_file',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'DEBUG',
            'propagate': True,
        },
        'mafiaapp.views': {
            'handlers': ['print_file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}

#SESSION_ENGINE = 'django.contrib.sessions.backends.db'
#SESSION_COOKIE_AGE = 1209600
MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

WSGI_APPLICATION = 'mafpub.wsgi.application'

# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

MAFPUB_POSTGRESQL_DB_HOST = os.environ.get('MAFPUB_POSTGRESQL_DB_HOST')
MAFPUB_POSTGRESQL_DB_PORT = os.environ.get('MAFPUB_POSTGRESQL_DB_PORT')
MAFPUB_POSTGRESQL_DB_USER = os.environ.get('MAFPUB_POSTGRESQL_DB_USERNAME')
MAFPUB_POSTGRESQL_DB_PASSWORD = os.environ.get('MAFPUB_POSTGRESQL_DB_PASSWORD')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'mafpub',
        'USER': MAFPUB_POSTGRESQL_DB_USER,
        'PASSWORD': MAFPUB_POSTGRESQL_DB_PASSWORD,
        'HOST': MAFPUB_POSTGRESQL_DB_HOST,
        'PORT': MAFPUB_POSTGRESQL_DB_PORT,
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    }]

# Internationalization
# https://docs.djangoproject.com/en/1.8/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

MAFPUB_EMAIL_HOST = os.environ.get('MAFPUB_EMAIL_HOST')
MAFPUB_EMAIL_HOST_USER = os.environ.get('MAFPUB_EMAIL_HOST_USER')
MAFPUB_EMAIL_HOST_PASSWORD = os.environ.get('MAFPUB_EMAIL_HOST_PASSWORD')
MAFPUB_EMAIL_PORT = os.environ.get('MAFPUB_EMAIL_PORT')

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = MAFPUB_EMAIL_HOST
EMAIL_HOST_USER = MAFPUB_EMAIL_HOST_USER
EMAIL_HOST_PASSWORD = MAFPUB_EMAIL_HOST_PASSWORD
EMAIL_PORT = MAFPUB_EMAIL_PORT

EMAIL_USE_TLS = True

DEFAULT_FROM_EMAIL = u'Галамафия 2.0 <noreply@maf.pub>'


MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

LOGIN_URL = '/'

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')

#SESSION_COOKIE_SECURE = True
#CSRF_COOKIE_SECURE = True
#SECURE_SSL_REDIRECT = True
