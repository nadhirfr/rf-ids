from django.conf.urls import url
from django.urls import path
from . import views
from channels.http import AsgiHandler

from . import consumers
from . import ddos

websocket_urlpatterns = [
    url(r'^ws/api/', consumers.TestConsumer, name='api_ws'),
]

http_urlpatterns = [
    url(r'^api/status/', consumers.ServiceStatus, name='api_status_http'),
    url(r'^api/', consumers.LongPollConsumer, name='api_http'),
    url(r"", AsgiHandler),
]