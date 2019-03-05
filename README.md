# django-no-view
Call django manager methods directly via REST api calls using JSON or easily changeable protocol.

This is very simple utility libarary to call django manager methods via REST JSON, there is no pip version yet so you have to clone it.

Sample usage
Add this line to your urls.py and you are good to go.
url(r'^customrpc/$', RPCEndpoint(lambda *args, **kwargs: True).get_view()), change "customrpc" to whatever regex you want to use.
