# django-no-view

#Call django manager methods directly via REST api calls using JSON or easily changeable protocol.

#This is very simple utility libarary to call django manager methods via REST JSON, there is no pip version yet so you have to clone it.

#Add this line to your urls.py and you are good to go.

url(r'^customrpc/$', RPCEndpoint(lambda *args, \**kwargs: True).get_view()),
change "customrpc" to whatever regex you want to use.

e.g urls.py file

```python


The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf.urls import url
from django.contrib import admin
from django.urls import path, include
from django_no_view.handler import RPCEndpoint,auth_fn_internal_rpc
from django.views.static import serve
from django.conf import settings


urlpatterns = [
    path('admin/', admin.site.urls),
    url(r'^static/(?P<path>.*)$', serve, {'document_root': settings.STATIC_ROOT}),
    url(r'^customrpc/$', RPCEndpoint(lambda *args, **kwargs: True).get_view()),
    #OR
    url(r'^securecustomrpc/$', RPCEndpoint(auth_fn_internal_rpc).get_view()),
    ]
