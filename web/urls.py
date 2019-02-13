# coding: utf-8
#

import os

from .views import LogoutHandler, MainHandler
from .views.device import (DeviceChangesWSHandler, DeviceItemHandler,
                           DeviceListHandler, APIUserDeviceHandler)
from .views.slave import SlaveHeartbeatWSHandler
from .views.upload import UploadItemHandler, UploadListHandler
from .views.user import APIUserHandler, UserHandler

urlpatterns = [
    (r"/", MainHandler),
    (r"/user", UserHandler),
    (r"/logout", LogoutHandler),
    (r"/uploads", UploadListHandler),
    (r"/uploads/(.*)", UploadItemHandler,
     {'path': os.path.join(os.getcwd(), 'uploads')}),
    (r"/devices", DeviceListHandler),
    (r"/devices/([^/]+)", DeviceItemHandler),
    (r"/websocket/devicechanges", DeviceChangesWSHandler),
    (r"/websocket/heartbeat", SlaveHeartbeatWSHandler),
    # (r"/device-control/([^/]+)", Device)
    # RESP API
    (r"/api/v1/user", APIUserHandler),
    (r"/api/v1/user/devices", APIUserDeviceHandler),
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
