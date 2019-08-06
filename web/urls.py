# coding: utf-8
#

import os

from .views import LogoutHandler, MainHandler
from .views.base import make_redirect_handler
from .views.device import (AndroidDeviceControlHandler, APIDeviceHandler,
                           APIDeviceListHandler, APIDevicePropertiesHandler,
                           APIUserDeviceActiveHandler, APIUserDeviceHandler,
                           AppleDeviceListHandler, DeviceChangesWSHandler,
                           DeviceItemHandler, DeviceListHandler)
from .views.group import (APIGroupUserListHandler, APIUserGroupListHandler,
                          UserGroupCreateHandler)
from .views.provider import ProviderHeartbeatWSHandler
from .views.upload import UploadItemHandler, UploadListHandler
from .views.user import (
    AdminListHandler, APIAdminListHandler, APIUserHandler,
    APIUserSettingsHandler, UserHandler)

urlpatterns = [
    (r"/", MainHandler),
    (r"/user", UserHandler),
    (r"/admin", AdminListHandler),
    (r"/user/group_create", UserGroupCreateHandler),
    (r"/logout", LogoutHandler),
    (r"/uploads", UploadListHandler),
    (r"/uploads/(.*)", UploadItemHandler, {
        'path': os.path.join(os.getcwd(), 'uploads')
    }),
    (r"/apples", AppleDeviceListHandler),
    (r"/devices", DeviceListHandler),
    (r"/devices/([^/]+)", DeviceItemHandler),
    (r"/devices/([^/]+)/remotecontrol", AndroidDeviceControlHandler),

    (r"/websocket/devicechanges", DeviceChangesWSHandler),
    (r"/websocket/heartbeat", ProviderHeartbeatWSHandler),
    # For compability of atx-server-1
    (r"/list", make_redirect_handler("/api/v1/devices")),
    # RESP API
    (r"/api/v1/devices", APIDeviceListHandler), # GET
    (r"/api/v1/devices/([^/]+)", APIDeviceHandler), # GET
    (r"/api/v1/devices/([^/]+)/properties", APIDevicePropertiesHandler), # GET, PUT
    (r"/api/v1/user", APIUserHandler), # GET
    (r"/api/v1/user/devices", APIUserDeviceHandler), # GET, POST, DELETE
    (r"/api/v1/user/devices/([^/]+)", APIUserDeviceHandler), # GET
    (r"/api/v1/user/devices/([^/]+)/active", APIUserDeviceActiveHandler), # GET
    (r"/api/v1/user/settings", APIUserSettingsHandler), # GET, PUT
    (r"/api/v1/admins", APIAdminListHandler), # GET, POST
    ## Group API
    # (r"/api/v1/user/groups/([^/]+)", APIUserGroupHandler), # GET, POST, DELETE  TODO(ssx)
    (r"/api/v1/user/groups", APIUserGroupListHandler), # GET, POST
    (r"/api/v1/groups/([^/]+)/users", APIGroupUserListHandler), # GET, TODO(POST)
    # GET /api/v1/devices
    # POST /api/v1/user/devices/{serial}/remoteConnect
    # DELETE /api/v1/user/devices/{serial}/remoteConnect
    # POST, GET /api/v1/user/devices/{serial}/shell
]
