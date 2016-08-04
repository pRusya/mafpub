"""myproject URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/1.8/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  url(r'^$', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  url(r'^$', Home.as_view(), name='home')
Including another URLconf
    1. Add an import:  from blog import urls as blog_urls
    2. Add a URL to urlpatterns:  url(r'^blog/', include(blog_urls))
"""
from django.conf import settings
from django.conf.urls import include, url
from django.contrib import admin
from django.http import HttpResponse
import os, sys

from django.conf.urls.static import static
from django.views.generic import RedirectView

def index(request):
    s = "<br>".join([k+'='+v for (k,v) in os.environ.items()])
    s += "<br><br>SESSION" + str(request.session.items())
    return HttpResponse("os.environ = %s" % s)

urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^identicon/', include('identicon.urls', namespace='identicon')),
    url(r'^', include('mafiaapp.urls', namespace="mafiaapp")),
    url(r'^api/', include('mafiaapp.api.urls', namespace="api_mafiaapp")),
    url(r'^test/$', index)
]