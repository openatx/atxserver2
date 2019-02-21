#!/usr/bin/env python
# coding: utf-8

import json
import time

from logzero import logger
from tornado import gen, websocket
from tornado.ioloop import IOLoop


class SafeWebSocket(websocket.WebSocketClientConnection):
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
            logger.warning("connection closed, try to reconnect")
        finally:
            time.sleep(3)


async def run_provider():
    ws = await websocket.websocket_connect(
        "ws://localhost:4000/websocket/heartbeat")
    ws.__class__ = SafeWebSocket
    await ws.write_message({"command": "ping"})
    msg = await ws.read_message()
    logger.info("read %s", msg)

    is_private = True

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
        "address": "192.168.1.100:7100",  # atx-agent listen address
        "data": {
            "udid": "abcdefg",
            "platform": "android",
            "present": True,
            "private": is_private,
            "properties": {
                "serial": "xyz234567890",
                "brand": 'Huawei',
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
    # set to offline
    # send {"udid": "abcdefg", "present": False}


if __name__ == '__main__':
    IOLoop.current().run_sync(main)
