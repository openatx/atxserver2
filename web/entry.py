# coding: utf-8
#
# only works for python3
#
from __future__ import print_function

import os

import tornado.concurrent
import tornado.ioloop
import tornado.web
import tornado.websocket

from .urls import urlpatterns


def make_app(login_handler, **settings):
    settings['template_path'] = 'templates'
    settings['static_path'] = 'static'
    settings['cookie_secret'] = os.environ.get("SECRET", "SECRET:_")
    settings['login_url'] = '/login'
    settings['websocket_ping_interval'] = 10

    urlpatterns.append((r"/login", login_handler))
    return tornado.web.Application(urlpatterns, **settings)
