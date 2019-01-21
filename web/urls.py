# coding: utf-8
#

from .views import MainHandler, LogoutHandler
from .views.device import (DeviceChangesWSHandler,
                           DeviceItemHandler, DeviceListHandler)
from .views.slave import SlaveHeartbeatWSHandler
from .views.user import UserHandler, APIUserHandler
from .views.upload import UploadListHandler


urlpatterns = [
    (r"/", MainHandler),
    (r"/user", UserHandler),
    (r"/logout", LogoutHandler),
    (r"/uploads", UploadListHandler),  # TODO
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

    # Upload
    # GET /uploads/12ldz98121231fasfvzsdf/com.example.helloworld-1.0.0.apk
]
