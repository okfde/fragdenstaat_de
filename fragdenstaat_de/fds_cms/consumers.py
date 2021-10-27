from websockets.exceptions import ConnectionClosedOK
from channels.generic.websocket import AsyncJsonWebsocketConsumer

from froide.helper.presence import get_presence_manager


PRESENCE_ROOM = "fds_cms.editplugin.{}"


class CMSPluginEditConsumer(AsyncJsonWebsocketConsumer):
    @property
    def pm(self):
        return get_presence_manager(self.room)

    async def connect(self):
        self.room = None
        user = self.scope["user"]
        if not user.is_staff:
            await self.close()
            return

        self.plugin_id = self.scope["url_route"]["kwargs"]["plugin_id"]
        self.room = PRESENCE_ROOM.format(self.plugin_id)

        await self.channel_layer.group_add(self.room, self.channel_name)
        await self.accept()
        await self.pm.touch(user)
        await self.update_userlist()

    async def update_userlist(self, action="joined"):
        users = await self.pm.list_present()
        userdict = {str(u.id): u.get_full_name() for u in users}

        await self.channel_layer.group_send(
            self.room,
            {
                "type": "userlist",
                "userdict": userdict,
                "user": {
                    "action": action,
                },
            },
        )

    async def receive_json(self, content):
        if content["type"] == "heartbeat":
            await self.pm.touch(self.scope["user"])
            return

    async def userlist(self, event):
        try:
            await self.send_json(
                {
                    "type": "userlist",
                    "userlist": [
                        name
                        for user_id, name in event["userdict"].items()
                        if user_id != str(self.scope["user"].id)
                    ],
                    "user": event["user"],
                }
            )
        except ConnectionClosedOK:
            pass

    async def disconnect(self, close_code):
        if self.room is None:
            return

        await self.channel_layer.group_discard(self.room, self.channel_name)
        await self.pm.remove(self.scope["user"])
        await self.update_userlist(action="left")
