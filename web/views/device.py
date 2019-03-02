# coding: utf-8
#

import json

import rethinkdb as r
from logzero import logger
from tornado.web import authenticated

from ..database import db, time_now
from ..libs import jsondate
from .base import AuthRequestHandler, BaseWebSocketHandler


class AcquireError(Exception):
    pass


class ReleaseError(Exception):
    pass


class APIUserDeviceHandler(AuthRequestHandler):
    """ device Acquire and Release """

    async def get_device(self, udid):
        data = await db.table("devices").get(udid).run()
        if not data:
            self.set_status(400)  # bad request
            self.write_json({
                "success": False,
                "description": "device not found " + id,
            })
            return

        # Find the highest priority source
        source = None
        priority = 0
        for s in data.get('sources', {}).values():
            if s['priority'] > priority:
                source = s
                priority = s['priority']
        data['bestSource'] = source

        self.write_json({
            "success": True,
            "data": data,
        })

    async def get(self, udid=None):
        """ get user current using devices """
        if udid:
            await self.get_device(udid)
            return

        data = await db.table("devices").filter({
            "present": True,
            "using": True,
            "userId": self.current_user.email,
        }).all()  # yapf: disable

        self.write_json({
            "success": True,
            "devices": data,
        })

    async def post(self):
        """ acquire device """
        data = self.get_payload()
        udid = data["udid"]
        try:
            await D(udid).acquire(self.current_user.email)
            self.write_json({
                "success": True,
                "description": "Device successfully added"
            })
        except AcquireError as e:
            self.set_status(403)  # forbidden
            self.write_json({
                "success": False,
                "description": "Device add failed: " + str(e),
            })

    async def delete(self, udid: str):
        """ release device """
        try:
            await D(udid).release(self.current_user.email)
            self.write_json({
                "success": True,
                "description": "Device successfully released"
            })
        except ReleaseError as e:
            self.set_status(403)  # forbidden
            self.write_json({
                "success": False,
                "description": "Device release failed: " + str(e),
            })


class AndroidDeviceControlHandler(AuthRequestHandler):
    """ device remote control """

    async def get(self, udid):
        device = await db.table("devices").get(udid).run()
        if not device:
            self.render("error.html", message="404 Device not found")
            return
        if not device['present']:
            self.render("error.html", message="Device is offline")
            return
        if not device.get("using"):
            try:
                await D(udid).acquire(self.current_user.email)
                self.render("remotecontrol.html", udid=udid)
            except AcquireError as e:
                self.render("error.html", message=str(e))
            finally:
                return
        if device.get('userId') != self.current_user.email:
            self.render(
                "error.html",
                message="Device is not owned by you!, owner is {}".format(
                    device.get('userId')))
            return
        self.render("remotecontrol.html", udid=udid)


class DeviceItemHandler(AuthRequestHandler):
    def get(self, udid):
        self.redirect("/api/v1/user/devices/" + udid)

    async def put(self, udid):
        pass


class AppleDeviceListHandler(AuthRequestHandler):
    def get(self):
        self.render("applelist.html")


class DeviceListHandler(AuthRequestHandler):
    """ Device List will show in first page """

    async def get(self):
        """ get data from database """
        if self.is_json_request or self.request.path == "/list":
            devices = await db.table("devices").order_by(
                r.desc("createdAt")).all()
            self.write_json({
                "success": True,
                "data": {
                    "devices": devices,
                    "count": await db.table("devices").count(),
                }
            })  # yapf: disable
            return
        self.render("index.html")

    # async def put(self):
    #     """ modify data in database """
    #     data = jsondate.loads(self.request.body)
    #     ret = await db.table("devices").save(data)
    #     self.write_json({"success": True, "data": ret})


class DeviceChangesWSHandler(BaseWebSocketHandler):
    def write_json(self, data):
        self.ws_connection.write_message(jsondate.dumps(data))

    async def open(self):
        self.__opened = True
        conn, feed = await db.table("devices").watch()
        with conn:
            while await feed.fetch_next():
                if not self.__opened:
                    break
                data = await feed.next()
                logger.info("feed data: %s", data)
                self.write_json({
                    "event": "insert" if data['old_val'] is None else 'update',
                    "data": data['new_val'],
                })  # yapf: disable

    def on_message(self, msg):
        logger.debug("receive message %s", msg)
        pass

    def on_close(self):
        self.__opened = False
        print("Websocket closed")


class D(object):
    """ Device object """

    def __init__(self, udid: str):
        self.udid = udid

    async def update(self, data: dict):
        return await db.table("devices").get(self.udid).update(data)

    async def acquire(self, email: str, idle_timeout: int = 100):
        """
        Raises:
            OccupyError
        """
        device = await db.table("devices").get(self.udid).run()
        if not device:
            raise AcquireError("device not exist")
        if not device.get('present'):  # 设备离线
            raise AcquireError("device absent")
        if device.get('using'):  # 使用中
            if device.get('userId') == email:
                # already used by ..{email}
                return
            raise AcquireError("device busy")
        if device.get("colding"):  # 冷却中
            raise AcquireError("device is colding")

        ret = await db.table("devices").get(self.udid).update({"using": True})
        if ret['skipped'] == 1:  # 被其他人占用了
            raise AcquireError(
                "not fast enough, device have been taken from others")
        await self.update({
            "userId": email,
            "usingBeganAt": time_now(),
            "lastActivatedAt": time_now(),
            "idleTimeout": idle_timeout,
        })

    async def release(self, email: str):
        """
        Raises:
            ReleaseError
        """
        device = await db.table("devices").get(self.udid).run()
        if not device:
            raise ReleaseError("device not exist")
        if device.get('userId') != email:
            raise ReleaseError("device is not owned by you")
        await self.update({
            "using": False,
            "userId": None
        })


# async def acquire_device(email: str, udid: str, idle_timeout: int = 600):
#     """
#     Raises:
#         OccupyError
#     """
#     device = await db.table("devices").get(udid).run()
#     if not device:
#         raise AcquireError("device not exist")
#     if not device.get('present'):
#         raise AcquireError("device absent")
#     if device.get('using'):
#         if device.get('userId') == email:
#             # already used by ..{email}
#             return
#         raise AcquireError("device busy")
#     if device.get("colding"):
#         raise AcquireError("device is colding")

#     ret = await db.table("devices").get(udid).update({"using": True})
#     if ret['skipped'] == 1:
#         raise AcquireError(
#             "not fast enough, device have been taken from others")
#     await db.table("devices").get(udid).update({
#         "userId": email,
#         "usingBeganAt": time_now(),
#         "lastActivatedAt": time_now(),
#         "idleTimeout": idle_timeout,
#     })

# async def release_device(email: str, udid: str):
#     """
#     Raises:
#         ReleaseError
#     """
#     device = await db.table("devices").get(udid).run()
#     if not device:
#         raise ReleaseError("device not exist")
#     if device.get('userId') != email:
#         raise ReleaseError("device is not owned by you")
#     await db.table("devices").get(udid).update({
#         "using": False,
#         "userId": None
#     })


class DeviceBookWSHandler(BaseWebSocketHandler):
    """ 连接成功时占用，断开时释放设备 """

    async def open(self, udid):
        if not self.current_user:
            self.write_message("need to login")
            self.close()
            return

        email = self.current_user.email
        try:
            await D(udid).acquire(email)
        except AcquireError as e:
            self.write_message(str(e))
            self.close()
            return

        self.write_message("device is yours")
