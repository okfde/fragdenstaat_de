from django.urls import path

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

from fragdenstaat_de.fds_cms.consumers import CMSPluginEditConsumer

from froide.routing import websocket_urls as froide_ws_urls

websocket_urls = froide_ws_urls + [
    path('fds-cms/edit-plugin/<int:plugin_id>/', CMSPluginEditConsumer)
]

application = ProtocolTypeRouter({
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter([
                path('ws/', URLRouter(websocket_urls))
            ])
        )
    ),
})
