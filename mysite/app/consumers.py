from channels.generic.websocket import AsyncWebsocketConsumer, WebsocketConsumer
from channels.generic.http import AsyncHttpConsumer
from channels.consumer import SyncConsumer
from asgiref.sync import async_to_sync
import json
import asyncio
import datetime
from channels.db import database_sync_to_async
from app.models import Alert, Status
from django.core.serializers import serialize, deserialize
from django.core.serializers.json import DjangoJSONEncoder
from datetime import datetime, timedelta
from urllib.parse import parse_qs

class TestConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # async_to_sync(
        await self.accept()
        await self.channel_layer.group_add("testGroup", self.channel_name)
        # I understand this next part is a bit weird, but I figured it
        # is the most concise way to explain my problem
        await self.channel_layer.group_send(
            "testGroup",
            {
                'type': "echo_msg",
                'msg': "sent from WebsocketConsumer",
            })

    async def echo_msg(self, message):
        pass

    async def run(self, message):
        print("Message to WebsocketConsumer", message)
        await self.send(json.dumps(message))

    async def alert(self, message):
        print("Message to WebsocketConsumer", message)
        await self.send(json.dumps(message))

    async def status(self, message):
        # print("Status : ", message['status'])
        await self.send(json.dumps(message))


class LongPollConsumer(AsyncHttpConsumer):
    async def handle(self, body):
        data = None
        try:
            query_string = self.scope['query_string']
            params = parse_qs(query_string)
            _seconds = 60
            _limit = 10
            # print(params.get(b'kuda', (None,))[0].decode("utf-8"))
            if params.get(b'limit', (None,))[0]:
                _limit = int(params.get(b'limit', (None,))[0].decode("utf-8"))
            if params.get(b'sec', (None,))[0]:
                _seconds = int(params.get(b'sec', (None,))[0].decode("utf-8"))
            # self.scope['method']
            alerts = await self.get_alert(nums=_limit, last_second=_seconds)
            data = json.dumps(list(alerts.values()), cls=DjangoJSONEncoder)
            await self.send_headers(headers=[
                (b"Content-Type", b"application/json"),
            ])
            # Headers are only sent after the first body event.
            # Set "more_body" to tell the interface server to not
            # finish the response yet:
            # await self.send_body(b"", more_body=False)
            await self.send_body(data.encode("utf-8"))
        except Exception as e:
            print(e)
        finally:
            pass
    
    @database_sync_to_async
    def get_alert(self, nums=10, last_second=60):
        time_threshold = datetime.now() - timedelta(seconds=last_second)
        print("Now : "+str(datetime.now()))
        print("A minute before now : "+str(time_threshold))
        _return = Alert.objects.filter(created_at__gt=time_threshold).order_by('-created_at')[:nums]
        return _return

class ServiceStatus(AsyncHttpConsumer):
    async def handle(self, body):
        data = None
        try:
            status = await self.get_status()
            data = {'status':status}
            await self.send_headers(headers=[
                (b"Content-Type", b"application/json"),
            ])
            # Headers are only sent after the first body event.
            # Set "more_body" to tell the interface server to not
            # finish the response yet:
            # await self.send_body(b"", more_body=False)
            await self.send_body(json.dumps(data).encode('utf-8'))
        except Exception as e:
            print(e)
        finally:
            pass
    
    @database_sync_to_async
    def get_status(self):
        return Status.objects.all()[0].status
        