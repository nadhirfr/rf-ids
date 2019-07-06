from channels.routing import ProtocolTypeRouter
from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter, ChannelNameRouter
import app.routing
from app.ddos import GenerateConsumer
from app import consumers
from django.conf.urls import url
from django.urls import path

application = ProtocolTypeRouter({
    # Empty for now (http->django views is added by default)
    'websocket': AuthMiddlewareStack(
        URLRouter(
            app.routing.websocket_urlpatterns
        )
    ),
    'http': 
    # AuthMiddlewareStack(
        URLRouter(
            app.routing.http_urlpatterns
        # )
    ),
    # 'http' : app,
    "channel": ChannelNameRouter({
        "alert-generate": GenerateConsumer,
        # "test_worker": app.consumers.TestWorker,
        # "thunbnails-delete": consumers.DeleteConsumer,
    }),
})