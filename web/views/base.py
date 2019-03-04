# coding:utf-8
#

import uuid

import tornado.web
import tornado.websocket
from bunch import Bunch
from tornado.ioloop import IOLoop
from tornado.web import authenticated
from tornado.escape import json_decode

from ..database import db, time_now
from ..libs import jsondate


class CurrentUserMixin(object):
    def bunchify(self, d: dict):
        return Bunch(d) if d else None

    async def get_current_user_async(self) -> Bunch:
        """
        method get_current_user can not be sync, so init current_user in in prepare

        Refs: https://www.tornadoweb.org/en/stable/guide/security.html#user-authentication
        """
        id = self.get_secure_cookie("user_id")  # here is bytes not str
        if id:
            id = id.decode()
        return self.bunchify(await db.table("users").get(id).run() if id else None)

    async def set_current_user(self, email: str, username: str):
        ret = await db.table("users").save({
            "email": email,
            "username": username
        })
        if ret['inserted']:
            await db.table("users").save({
                "secretKey": "S:" + str(uuid.uuid4()),
                "createdAt": time_now(),
                "lastLoggedInAt": time_now(),
            }, ret['id'])
        elif ret['unchanged']:
            await db.table("users").save({
                "lastLoggedInAt": time_now(),
            }, ret['id'])

        self.set_secure_cookie("user_id", ret['id'])


class BaseRequestHandler(CurrentUserMixin, tornado.web.RequestHandler):
    """
    Note:
        CurrentUserMixin should before RequestHandler to make sure get_current_user override
    """

    async def prepare(self):
        self.current_user = await self.get_current_user_async()

    def write_json(self, data):
        assert isinstance(data, dict)
        self.set_header("Content-Type", "application/json; charset=utf-8")
        content = jsondate.dumps(data)
        self.write(content)

    def get_payload(self):
        return json_decode(self.request.body)

    @property
    def is_json_request(self):
        return self.get_argument('json', None) is not None

    async def get(self, *args):
        if self.get_argument('json', None) is not None:
            await self.get_json(*args)
            return
        await self.get_html(*args)

    async def get_html(self, *args):
        pass

    async def get_json(self, *args):
        pass


class AuthRequestHandler(BaseRequestHandler):
    """ request user logged in before http request """

    async def prepare(self):
        await super().prepare()
        authenticated(lambda x: None)(self)


class BaseWebSocketHandler(CurrentUserMixin,
                           tornado.websocket.WebSocketHandler):
    """ update current_user when websocket created """

    async def prepare(self):
        self.current_user = await self.get_current_user_async()

    def check_origin(self, origin):
        return True


class CorsMixin(object):
    CORS_ORIGIN = '*'
    CORS_METHODS = 'GET,POST,OPTIONS'
    CORS_CREDENTIALS = True
    CORS_HEADERS = "x-requested-with"

    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", self.CORS_ORIGIN)
        self.set_header("Access-Control-Allow-Headers", self.CORS_HEADERS)
        self.set_header('Access-Control-Allow-Methods', self.CORS_METHODS)

    def options(self):
        # no body
        self.set_status(204)
        self.finish()


def make_redirect_handler(url:str) -> tornado.web.RequestHandler:
    class RedirectHandler(tornado.web.RequestHandler):
        def get(self):
            return self.redirect(url)

    return RedirectHandler
    