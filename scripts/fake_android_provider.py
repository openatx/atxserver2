#!/usr/bin/env python
# coding: utf-8

import json
import shutil
import subprocess
import sys
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

import requests
import tornado.web
from logzero import logger
from tornado import gen, websocket
from tornado.concurrent import run_on_executor
from tornado.ioloop import IOLoop
from tornado.tcpclient import TCPClient
from tornado.web import RequestHandler
from tornado.websocket import WebSocketHandler


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
            # print("Read", self.read_bytes(4))
            length = int(await self.read_bytes(4), 16)
            print("Len:", length)
            message = await self.read_bytes(length)
            print("Message:", message)
        elif data == FAIL:
            length = int(await self.read_bytes(4), 16)
            print("Len:", length)
            message = await self.read_bytes(length)
            print("Message:", message)
        else:
            print("Unknown head:", data)

    async def send_cmd(self, cmd: str):
        await self._stream.write("{:04x}{}".format(len(cmd),
                                                   cmd).encode('utf-8'))

    async def read_bytes(self, num_bytes: int):
        return (await self._stream.read_bytes(num_bytes)).decode()


class AppHandler(RequestHandler):
    _thread_pool = ThreadPoolExecutor(max_workers=4)

    @run_on_executor(executor='_thread_pool')
    def background_task(self, url):
        """ download and install """
        r = requests.get(url, stream=True)
        print(r.status_code)
        print(r.headers)
        with tempfile.NamedTemporaryFile(suffix=".apk") as fp:
            logger.debug("create temp-apk-file %s", fp.name)
            shutil.copyfileobj(r.raw, fp)
            fp.seek(0)
            logger.debug("install apk")
            p = subprocess.Popen(["adb", "install", "-r", fp.name],
                                 stdout=sys.stdout,
                                 stderr=sys.stderr)
            p.wait(timeout=60)
            logger.debug("done")
            # logger.debug("output: %s")

    def post(self):
        url = self.get_argument("url")
        IOLoop.current().spawn_callback(self.background_task, url)
        self.write({
            "success": True,
            "url": url,
        })

    def get(self):
        self.write("IMOK")


class PushUrlWSHandler(WebSocketHandler):
    """ download file to device through file url """

    def open(self):
        pass

    def on_message(self, message):
        pass

    def on_close(self):
        pass


async def main():
    adb = SimpleADB()
    await adb.watch()
    # return

    while True:
        try:
            await run_provider("localhost:4000")
        except TypeError:
            pass
            logger.warning("connection closed, try to reconnect")
        finally:
            time.sleep(3)


async def run_provider(server_addr: str):
    ws = await websocket.websocket_connect("ws://" + server_addr +
                                           "/websocket/heartbeat")
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
    # print(msg)
    await ws.write_message({
        "command": "update",
        "address": "192.168.0.108:7912",  # atx-agent listen address
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


def run_server():
    app = tornado.web.Application([
        (r"/apps", AppHandler),
    ], debug=True)
    app.listen("7224")
    IOLoop.current().spawn_callback(main)
    IOLoop.current().start()


if __name__ == '__main__':
    IOLoop.current().run_sync(main)
    # run_server()
