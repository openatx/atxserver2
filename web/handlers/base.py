# coding:utf-8
# 

import tornado.web
from bunch import Bunch

from ..utils import jsondate_dumps


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
