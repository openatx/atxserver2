#!/usr/bin/env python
# coding: utf-8

import asyncio as aio
import json
import time

from tornado import websocket
from tornado.ioloop import IOLoop


class WebSocket(websocket.WebSocketClientConnection):
    async def write_message(self, message, binary=False):
        if isinstance(message, dict):
            message = json.dumps(message)
        return await super().write_message(message)


async def main():
    ws = await websocket.websocket_connect("ws://localhost:4000/websocket/heartbeat")
    ws.__class__ = WebSocket
    await ws.write_message({"command": "ping"})
    msg = await ws.read_message()
    print(msg)


if __name__ == '__main__':
    IOLoop.current().run_sync(main)
