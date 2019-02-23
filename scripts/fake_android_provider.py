#!/usr/bin/env python
# coding: utf-8

import json
import time

from logzero import logger
from tornado import gen, websocket
from tornado.ioloop import IOLoop
from tornado.tcpclient import TCPClient


class SafeWebSocket(websocket.WebSocketClientConnection):
    async def write_message(self, message, binary=False):
        if isinstance(message, dict):
            message = json.dumps(message)
        return await super().write_message(message)


OKAY = "OKAY"
FAIL = "FAIL"


class SimpleADB(object):
    def __init__(self):
        self._stream = None
        pass

    async def watch(self):
        print("Watch")
        self._stream = await TCPClient().connect('127.0.0.1', 5037)
        await self.send_cmd("host:devices")
        data = await self.read_bytes(4)
        if data == OKAY:
            length = int(self.read_bytes(4), 16)
            print("Len:", length)
            message = self.read_bytes(length)
            print("Message:", message)
        elif data == FAIL:
            length = int(self.read_bytes(4), 16)
            print("Len:", length)
            message = self.read_bytes(length)
            print("Message:", message)
        else:
            print("Unknown head:", data)

    async def send_cmd(self, cmd: str):
        await self._stream.write("{:04x}{}".format(len(cmd), cmd))

    async def read_bytes(self, num_bytes: int):
        return await self._stream.read_bytes(num_bytes).decode()


async def main():
    while True:
        try:
            adb = SimpleADB()
            await adb.watch()
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
