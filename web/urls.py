# coding: utf-8
#

from .views import MainHandler, LogoutHandler, UploadHandler
from .views.device import (DeviceChangesWSHandler,
                           DeviceItemHandler, DeviceListHandler)
from .views.slave import SlaveHeartbeatWSHandler
from .views.user import UserHandler, APIUserHandler

urlpatterns = [
    (r"/", MainHandler),
    (r"/user", UserHandler),
    (r"/api/user", APIUserHandler),
    (r"/logout", LogoutHandler),
    (r"/upload", UploadHandler),
    (r"/devices", DeviceListHandler),
    (r"/devices/([^/]+)", DeviceItemHandler),
    (r"/websocket/devicechanges", DeviceChangesWSHandler),
    (r"/websocket/heartbeat", SlaveHeartbeatWSHandler),
    # (r"/device-control/([^/]+)", Device)
]
