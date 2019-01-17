# coding: utf-8
#
# only works for python3
#
from __future__ import print_function

import argparse
import datetime
import json
import os
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from pprint import pprint

import rethinkdb as r
import tornado.concurrent
import tornado.ioloop
import tornado.web
import tornado.websocket
from bunch import Bunch
from logzero import logger
from tornado import gen
from tornado.httpclient import AsyncHTTPClient
from tornado.log import enable_pretty_logging
from tornado.web import authenticated

from . import settings
from .database import db, jsondate_loads
from .handlers import BaseRequestHandler, OpenIdLoginHandler, SimpleLoginHandler
from .utils import jsondate_dumps


class LogoutHandler(BaseRequestHandler):
    def get(self):
        self.clear_all_cookies()
        self.redirect("/login")


class MainHandler(BaseRequestHandler):
    def get(self):
        self.redirect("/devices")


class UploadHandler(BaseRequestHandler):
    _thread_pool = ThreadPoolExecutor(max_workers=4)

    @tornado.concurrent.run_on_executor(executor='_thread_pool')
    def upload_image(self, binary_data):
        # return fpclient.upload_image_binary(binary_data)
        pass

    @gen.coroutine
    def post(self):
        # Only tornado 5.x.x support await
        # But tornado 5.x.x not support rethinkdb
        finfo = self.request.files["file"][0]
        url = yield self.upload_image(finfo['body'])
        self.write(url)


class DeviceItemHandler(BaseRequestHandler):
    async def put(self, id):
        pass

    async def get_json(self, id):
        data = await db.table("records").get(id)
        self.write_json({
            "success": True,
            "data": data,
        })

    async def get_html(self, id):
        self.render("record.html")


class DeviceListHandler(BaseRequestHandler):
    """ Device List will show in first page """

    @authenticated
    async def get(self):
        """ get data from database """
        if self.get_argument('json', None) is not None:
            self.write_json({
                "success": True,
                "data": await db.table("devices").get_all(limit=50, desc="createdAt"),
            }) # yapf: disable
            return
        self.render("index.html")

    async def post(self):
        """ add data into database """
        data = jsondate_loads(self.request.body)
        id = await db.table("devices").save(data)
        self.write_json({"id": id, "data": data})


class DeviceChangesWSHandler(tornado.websocket.WebSocketHandler):
    def write_json(self, data):
        self.ws_connection.write_message(jsondate_dumps(data))

    async def open(self):
        self.__opened = True
        conn, feed = await db.table("devices").watch()
        with conn:
            while await feed.fetch_next():
                if not self.__opened:
                    break
                data = await feed.next()
                self.write_json({
                    "event": "insert" if data['old_val'] is None else 'update',
                    "data": data['new_val'],
                }) # yapf: disable

    def on_message(self, msg):
        logger.debug("receive message %s", msg)
        pass

    def on_close(self):
        self.__opened = False
        print("Websocket closed")


def make_app(login_handler, **settings):
    settings['template_path'] = 'templates'
    settings['static_path'] = 'static'
    settings['cookie_secret'] = os.environ.get("SECRET", "SECRET:_")
    settings['login_url'] = '/login'
    settings['websocket_ping_interval'] = 10

    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/login", login_handler),
        (r"/logout", LogoutHandler),
        (r"/upload", UploadHandler),
        (r"/devices", DeviceListHandler),
        (r"/devices/([^/]+)", DeviceItemHandler),
        (r"/websocket/devicechanges", DeviceChangesWSHandler),
    ], **settings)
