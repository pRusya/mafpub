"""
WSGI config for myproject project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/howto/deployment/wsgi/
"""

import os
import sys

from django.core.wsgi import get_wsgi_application

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

with open(BASE_DIR+'/mafpub/secret.txt', 'r') as file:
	lines = file.readlines()
	for line in lines:
		k, v = line.strip().split('=')
		os.environ.setdefault(k, v)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "mafpub.settings_dev")

application = get_wsgi_application()
