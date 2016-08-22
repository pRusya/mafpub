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
DJ_PROJECT_DIR = os.path.dirname(__file__)
BASE_DIR = os.path.dirname(DJ_PROJECT_DIR)
WSGI_DIR = os.path.dirname(BASE_DIR)
REPO_DIR = os.path.dirname(WSGI_DIR)
DATA_DIR = os.environ.get('OPENSHIFT_DATA_DIR', BASE_DIR)

import sys
sys.path.append(os.path.join(REPO_DIR, 'libs'))
import secrets
SECRETS = secrets.getter(os.path.join(DATA_DIR, 'secrets.json'))

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/1.8/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = SECRETS['secret_key']

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True  # os.environ.get('DEBUG') == 'True'

from socket import gethostname
ALLOWED_HOSTS = [
    gethostname(), # For internal OpenShift load balancer security purposes.
    os.environ.get('OPENSHIFT_APP_DNS'), # Dynamically map to the OpenShift gear name.
    #'example.com', # First DNS alias (set up in the app)
    #'www.example.com', # Second DNS alias (set up in the app)
]


# Application definition

INSTALLED_APPS = (
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'mafiaapp.apps.MafiaAppConfig',
    'identicon.apps.IdenticonConfig',
    # third party
    # 'silk',
    'widget_tweaks',
    'pagedown',
)

MIDDLEWARE_CLASSES = (
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.auth.middleware.SessionAuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    # third party
    # 'silk.middleware.SilkyMiddleware',
)

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

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

# SILKY_AUTHENTICATION = True  # User must login
# SILKY_AUTHORISATION = True  # User must have permissions

WSGI_APPLICATION = 'mafpub.wsgi.application'


# Database
# https://docs.djangoproject.com/en/1.8/ref/settings/#databases

POSTGRESQL_DB_HOST = os.environ.get('OPENSHIFT_POSTGRESQL_DB_HOST')
POSTGRESQL_DB_PORT = os.environ.get('OPENSHIFT_POSTGRESQL_DB_PORT')
POSTGRESQL_DB_USER = os.environ.get('OPENSHIFT_POSTGRESQL_DB_USERNAME')
POSTGRESQL_DB_PASSWORD = os.environ.get('OPENSHIFT_POSTGRESQL_DB_PASSWORD')

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': 'mafpub',
        'USER': POSTGRESQL_DB_USER,
        'PASSWORD': POSTGRESQL_DB_PASSWORD,
        'HOST': POSTGRESQL_DB_HOST,
        'PORT': POSTGRESQL_DB_PORT,
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

OPENSHIFT_DATA_DIR = os.environ.get('OPENSHIFT_DATA_DIR')

MEDIA_ROOT = os.path.join(OPENSHIFT_DATA_DIR, 'media')
MEDIA_URL = '/media/'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/1.8/howto/static-files/

LOGIN_URL = '/'

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(OPENSHIFT_DATA_DIR, 'static')
STATICFILES_DIRS = (
    os.path.join(BASE_DIR, "mafpub", "static"),
)
