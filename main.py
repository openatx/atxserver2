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

import settings
from auth import AuthError, OpenIdMixin
from database import db, jsondate_loads


def _data_handler(obj):
    return obj.isoformat() if hasattr(obj, "isoformat") else obj


def jsondate_dumps(data):
    assert isinstance(data, dict)
    return json.dumps(data, default=_data_handler)


class BaseRequestHandler(tornado.web.RequestHandler):
    __user_db = {}

    def get_current_user(self):
        """ https://www.tornadoweb.org/en/stable/guide/security.html#user-authentication """
        id = self.get_secure_cookie("user_id")  # here is bytes not str
        if id:
            id = id.decode()
        info = self.__user_db.get(id)
        return Bunch(info) if info else None

    def set_current_user(self, email, username):
        id = email
        self.set_secure_cookie("user_id", id)
        info = dict(username=username, email=email)
        self.__user_db[id] = info

    def write_json(self, data):
        assert isinstance(data, dict)
        self.set_header("Content-Type", "application/json; charset=utf-8")
        content = jsondate_dumps(data)
        self.write(content)

    async def get(self, *args):
        if self.get_argument('json', None) is not None:
            await self.get_json(*args)
            return
        await self.get_html(*args)

    async def get_html(self, *args):
        pass

    async def get_json(self, *args):
        pass


class OpenIdLoginHandler(BaseRequestHandler, OpenIdMixin):
    _OPENID_ENDPOINT = 'https://login.netease.com/openid/'

    async def get(self):
        if self.get_argument("openid.mode", False):
            try:
                user = await self.get_authenticated_user()
            except AuthError as e:
                self.write(
                    "<code>Auth error: {}</code> <a href='/login'>Login</a>".
                    format(e))
            else:
                logger.info("User info: %s", user)
                self.set_current_user(user['email'], user['username'])
                next_url = self.get_argument('next', '/')
                self.redirect(next_url)
        else:
            self.authenticate_redirect()


class SimpleLoginHandler(BaseRequestHandler):
    def get(self):
        self.set_cookie("next", self.get_argument("next", "/"))
        self.write('<html><body><form action="/login" method="post">'
                   'Name: <input type="text" name="name">'
                   '<input type="submit" value="Sign in">'
                   '</form></body></html>')

    def post(self):
        name = self.get_argument("name")
        email = name + "@anonymous.com"
        self.set_current_user(email, name)
        next_url = self.get_cookie("next", "/")
        self.clear_cookie("next")
        self.redirect(next_url)


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


def machine_ip():
    """ return current machine ip """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    try:
        return s.getsockname()[0]
    finally:
        s.close()


_auth_handlers = {
    "simple": SimpleLoginHandler,
    "openid": OpenIdLoginHandler,
}


def main():
    parser = argparse.ArgumentParser()
    # yapf: disable
    parser.add_argument('-p', '--port', type=int, default=4000, help='listen port')
    parser.add_argument('-d', '--debug', action='store_true', help='open debug log, and open hot reload')
    parser.add_argument('--auth', type=str, default='simple', choices=_auth_handlers.keys(), help='authentication method')
    parser.add_argument('--auth-conf-file', type=argparse.FileType('r'), help='authentication config file')
    # yapf: enable

    args = parser.parse_args()
    print(args)
    enable_pretty_logging()

    db.setup()

    ioloop = tornado.ioloop.IOLoop.current()

    # TODO(ssx): for debug use
    async def dbtest():
        items = await db.table("devices").get_all(
            limit=2, rsql_hook=lambda q: q.order_by(r.desc("createdAt")))
        for item in items:
            pprint(item)

    ioloop.spawn_callback(dbtest)

    login_handler = _auth_handlers[args.auth]
    app = make_app(login_handler, debug=args.debug)
    app.listen(args.port)
    logger.info("listen on port http://%s:%d", machine_ip(), args.port)
    try:
        ioloop.start()
    except KeyboardInterrupt:
        ioloop.stop()


if __name__ == "__main__":
    main()
