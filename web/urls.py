# coding: utf-8
#

import os

from .views import LogoutHandler, MainHandler
from .views.device import (DeviceChangesWSHandler, DeviceItemHandler,
                           DeviceListHandler, APIUserDeviceHandler, DeviceControlHandler)
from .views.provider import ProviderHeartbeatWSHandler
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
    (r"/devices/([^/]+)/remotecontrol", DeviceControlHandler),
    (r"/websocket/devicechanges", DeviceChangesWSHandler),
    (r"/websocket/heartbeat", ProviderHeartbeatWSHandler),
    # (r"/device-control/([^/]+)", Device)
    # For compability of atx-server1
    (r"/list", DeviceListHandler),
    # RESP API
    (r"/api/v1/user", APIUserHandler),
    (r"/api/v1/user/devices", APIUserDeviceHandler),
    (r"/api/v1/user/devices/([^/]+)", APIUserDeviceHandler),
    # GET /api/v1/devices
    # GET /api/v1/devices/{serial}
    # GET /api/v1/user/devices
    # POST /api/v1/user/devices/{serial}/remoteConnect
    # DELETE /api/v1/user/devices/{serial}/remoteConnect
    # POST, GET /api/v1/user/devices/{serial}/shell

    # Upload
    # GET /uploads/12ldz98121231fasfvzsdf/com.example.helloworld-1.0.0.apk
]
