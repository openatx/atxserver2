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
    (r"/logout", LogoutHandler),
    (r"/upload", UploadHandler),
    (r"/devices", DeviceListHandler),
    (r"/devices/([^/]+)", DeviceItemHandler),
    (r"/websocket/devicechanges", DeviceChangesWSHandler),
    (r"/websocket/heartbeat", SlaveHeartbeatWSHandler),
    # (r"/device-control/([^/]+)", Device)
    # RESP API
    (r"/api/v1/user", APIUserHandler),
    # GET /api/v1/devices
    # GET /api/v1/devices/{serial}
    # GET /api/v1/user/devices
    # POST /api/v1/user/devices
    # DELETE /api/v1/user/devices/{serial}
    # POST /api/v1/user/devices/{serial}/remoteConnect
    # DELETE /api/v1/user/devices/{serial}/remoteConnect
]
