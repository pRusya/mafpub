#!/usr/bin/env python

from setuptools import setup

setup(name='mafpub',
      version='1.0',
      description='mafpub for OpenShift',
      author='Ruslan Pozin',
      author_email='ruslan.pozin@gmail.com',
      url='http://www.python.org/sigs/distutils-sig/',
      install_requires=[
        'Django==1.8.12',
        'Pillow==3.1.1',
        'requests',
        'django-widget-tweaks==1.4.1'
      ],
      dependency_links=[
        'https://pypi.python.org/simple/django/'
      ],
     )
