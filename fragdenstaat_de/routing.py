from django.core.asgi import get_asgi_application
from django.urls import path

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from fragdenstaat_de.fds_cms.consumers import CMSPluginEditConsumer
from froide_campaign.consumers import CampaignLiveConsumer

from froide.routing import websocket_urls as froide_ws_urls

websocket_urls = froide_ws_urls + [
    path("fds-cms/edit-plugin/<int:plugin_id>/", CMSPluginEditConsumer.as_asgi()),
    path("campaign/live/<int:pk>/", CampaignLiveConsumer.as_asgi()),
]


class LifespanApp:
    """
    temporary shim for https://github.com/django/channels/issues/1216
    needed so that hypercorn doesn't display an error.
    this uses ASGI 2.0 format, not the newer 3.0 single callable
    """

    async def __call__(self, scope, receive, send):
        if scope["type"] == "lifespan":
            while True:
                message = await receive()
                if message["type"] == "lifespan.startup":
                    await send({"type": "lifespan.startup.complete"})
                elif message["type"] == "lifespan.shutdown":
                    await send({"type": "lifespan.shutdown.complete"})
                    return


application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "lifespan": LifespanApp(),
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter([path("ws/", URLRouter(websocket_urls))]))
        ),
    }
)
