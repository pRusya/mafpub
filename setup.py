#!/usr/bin/env python

from setuptools import setup

setup(name='mafpub',
      version='1.0',
      description='mafpub for OpenShift v2',
      author='Ruslan Pozin',
      author_email='ruslan.pozin@gmail.com',
      url='http://www.python.org/sigs/distutils-sig/',
      install_requires=[
        'Django==1.8.12',
        'Pillow==3.1.1',
        'requests',
        'django-summernote==0.8.5',
      ],
      dependency_links=[
        'https://pypi.python.org/simple/django/',
        'git+https://github.com/prusya/django-visitor-activity.git',
      ],
     )
