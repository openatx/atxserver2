#!/usr/bin/env python
# coding: utf-8

import asyncio as aio
import json
import time

from logzero import logger
from tornado import gen, websocket
from tornado.ioloop import IOLoop


class WebSocket(websocket.WebSocketClientConnection):
    async def write_message(self, message, binary=False):
        if isinstance(message, dict):
            message = json.dumps(message)
        return await super().write_message(message)


async def main():
    while True:
        try:
            await run_provider()
        except TypeError:
            pass
        finally:
            time.sleep(3)


async def run_provider():
    ws = await websocket.websocket_connect(
        "ws://localhost:4000/websocket/heartbeat")
    ws.__class__ = WebSocket
    await ws.write_message({"command": "ping"})
    msg = await ws.read_message()
    print(msg)

    await ws.write_message({
        "command": "handshake",
        "name": "mac",
        "owner": "codeskyblue@gmail.com",
        "priority": 2
    })  # priority the large the importanter
    msg = await ws.read_message()
    print(msg)
    await ws.write_message({
        "command": "update",
        "address": "10.242.88.46:7912",
        "data": {
            "udid": "1plus",
            "platform": "android",
            "present": True,
            "properties": {
                "serial": "11471d3e",
                "brand": 'One',
                "version": "7.0.1",
            }
        }
    })
    await gen.sleep(2)
    while 1:
        await ws.write_message({"command": "ping"})
        msg = await ws.read_message()
        logger.debug("receive: %s", msg)
        await gen.sleep(1)


if __name__ == '__main__':
    IOLoop.current().run_sync(main)
