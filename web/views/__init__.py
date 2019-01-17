# coding: utf-8
#
from concurrent.futures import ThreadPoolExecutor

import tornado.concurrent
from tornado import gen

from .base import BaseRequestHandler
from .login import OpenIdLoginHandler, SimpleLoginHandler


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
