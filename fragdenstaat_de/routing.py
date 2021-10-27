from django.urls import path
from django.core.asgi import get_asgi_application

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

from fragdenstaat_de.fds_cms.consumers import CMSPluginEditConsumer
from froide_campaign.consumers import CampaignLiveConsumer

from froide.routing import websocket_urls as froide_ws_urls

websocket_urls = froide_ws_urls + [
    path("fds-cms/edit-plugin/<int:plugin_id>/", CMSPluginEditConsumer.as_asgi()),
    path("campaign/live/<int:pk>/", CampaignLiveConsumer.as_asgi()),
]

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter([path("ws/", URLRouter(websocket_urls))]))
        ),
    }
)
