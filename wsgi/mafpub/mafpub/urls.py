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
from django.conf.urls import include, url
from django.contrib import admin


urlpatterns = [
    url(r'^admin/', admin.site.urls),
    url(r'^identicon/', include('identicon.urls', namespace='identicon')),
    url(r'^', include('mafiaapp.urls', namespace="mafiaapp")),
    # url(r'^api/', include('mafiaapp.api.urls', namespace="api_mafiaapp")),
    # url(r'^test/$', index)#
]

urlpatterns += [url(r'^silk/', include('silk.urls', namespace='silk'))]
