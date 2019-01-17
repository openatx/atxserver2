# coding: utf-8
#

from .views import MainHandler, LogoutHandler, UploadHandler
from .views.device import (DeviceChangesWSHandler, DeviceHeartbeatWSHandler,
                           DeviceItemHandler, DeviceListHandler)

urlpatterns = [
    (r"/", MainHandler),
    (r"/logout", LogoutHandler),
    (r"/upload", UploadHandler),
    (r"/devices", DeviceListHandler),
    (r"/devices/([^/]+)", DeviceItemHandler),
    (r"/websocket/devicechanges", DeviceChangesWSHandler),
    (r"/websocket/heartbeat", DeviceHeartbeatWSHandler),
]
