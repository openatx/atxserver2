# coding: utf-8
#

from .base import BaseRequestHandler
from tornado.web import authenticated


class UserHandler(BaseRequestHandler):
    @authenticated
    def get(self):
        self.render("user.html")


class APIUserHandler(BaseRequestHandler):
    @authenticated
    async def get(self):
        self.write_json(self.current_user)
