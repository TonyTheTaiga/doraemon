import logging

from starlette.websockets import WebSocket, WebSocketDisconnect
from tortoise.transactions import atomic

from ekiden import database
from ekiden.nips import Filters
from ekiden.relay import AsyncRelay
from ekiden.subscriptions import Subscription, SubscriptionPool

logging.basicConfig(level=logging.INFO)


class Hoshi:
    sub_pool = SubscriptionPool()
    relay = AsyncRelay(sub_pool=sub_pool)

    async def __call__(self, scope, receive, send):
        websocket = WebSocket(scope=scope, receive=receive, send=send)
        await self.endpoint(websocket)

    async def endpoint(self, websocket: WebSocket):
        await websocket.accept()
        try:
            while True:
                match await websocket.receive_json():
                    case ["EVENT", message]:
                        await self.handle_event(websocket=websocket, message=message)
                    case ["REQ", subscription_id, filters_dict]:
                        await self.handle_request(
                            websocket=websocket, subscription_id=subscription_id, filters_dict=filters_dict
                        )
                    case ["CLOSE", subscription_id]:
                        await self.handle_close(websocket)

        except WebSocketDisconnect:
            await self.handle_disconnect(websocket)

    async def handle_event(self, websocket: WebSocket, message: dict):
        #     """
        #     used to publish events
        #     """
        response = await self.relay.event(message)
        await websocket.send_text(response)

    async def handle_request(self, websocket: WebSocket, subscription_id: str, filters_dict: dict):
        """
        used to request events and subscribe to new updates
        """
        sub = Subscription(
            filters=Filters.parse_obj(filters_dict),
            websocket=websocket,
            subscription_id=subscription_id,
        )
        await self.sub_pool.add_subscription(subscription=sub)
        # set sane cap
        limit = sub.filters.limit if sub.filters.limit else 100
        for event in await database.Event.all().limit(limit):
            await sub.send(event.nipple())

    async def handle_close(self, websocket: WebSocket):
        #     """
        #     used to stop previous subscriptions
        #     """
        await self.handle_disconnect(websocket)

    async def handle_disconnect(self, websocket: WebSocket):
        subscription = await self.sub_pool.get_subscription(websocket=websocket)
        if subscription:
            await self.sub_pool.remove_subscription(subscription)
