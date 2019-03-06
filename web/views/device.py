# coding: utf-8
#

import json
import datetime

import rethinkdb as r
from logzero import logger
from tornado.web import authenticated
from tornado.ioloop import IOLoop
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado import gen

from ..database import db, time_now
from ..libs import jsondate
from .base import AuthRequestHandler, BaseWebSocketHandler, BaseRequestHandler, CorsMixin


class AcquireError(Exception):
    pass


class ReleaseError(Exception):
    pass


class APIDeviceListHandler(CorsMixin, BaseRequestHandler):
    async def get(self):
        devices = await db.table_devices.without("sources", "source").order_by(
            r.desc("createdAt")).all()
        self.write_json({
            "success": True,
            "data": {
                "devices": devices,
                "count": await db.table_devices.count(),
            }
        })  # yapf: disable

    # async def put(self):
    #     """ modify data in database """
    #     data = jsondate.loads(self.request.body)
    #     ret = await db.table("devices").save(data)
    #     self.write_json({"success": True, "data": ret})


class APIUserDeviceActiveHandler(AuthRequestHandler):
    """ active update time """

    async def get(self, udid):
        # """ update lastActivatedAt """
        ret = await db.table("devices").filter({
            "using": True,
            "udid": udid,
            "userId": self.current_user.email
        }).update({"lastActivatedAt": time_now()}) # yapf: disable
        if ret['replaced']:
            self.write_json({
                "success": True,
                "description": "Device activated time is updated"
            })
        else:
            self.set_status(400)
            self.write_json({
                "success": False,
                "description": "Device is not owned by you"
            })


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
        if data.get('userId') != self.current_user.email:
            self.set_status(403)
            self.write_json({
                "success": False,
                "description": "you have to acquire it before access device info",
            }) # yapf: disable
            return

        # Find the highest priority source
        source = None
        priority = 0
        for s in data.get('sources', {}).values():
            if s['priority'] > priority:
                source = s
                priority = s['priority']
        data['source'] = source

        self.write_json({
            "success": True,
            "data": data,
        })

    async def get(self, udid=None):
        """ get user current using devices """
        if udid:
            await self.get_device(udid)
            return

        data = await db.table_devices.filter({
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

    def render_remotecontrol(self, device: dict):
        platform = device['platform']
        udid = device['udid']
        if platform == 'android':
            self.render("remotecontrol_android.html", udid=udid)
        elif platform == 'apple':
            self.render("remotecontrol_apple.html", udid=udid)
        else:
            self.render(
                "error.html",
                message="Platform {} is not support remote control".format(
                    platform))

    async def get(self, udid):
        device = await db.table("devices").get(udid).run()
        if not device:
            self.render("error.html", message="404 Device not found")
            return

        if not device.get("sources"):
            self.render("error.html", message="Device is not present")
            return
        if not device.get("using"):
            try:
                await D(udid).acquire(self.current_user.email)
                self.render_remotecontrol(device)
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

        self.render_remotecontrol(device)


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
        self.render("index.html")


class DeviceChangesWSHandler(BaseWebSocketHandler):
    def write_json(self, data):
        self.ws_connection.write_message(jsondate.dumps(data))

    async def open(self):
        self.__opened = True
        conn, feed = await db.table_devices.watch()
        with conn:
            while await feed.fetch_next():
                if not self.__opened:
                    break
                data = await feed.next()
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

    async def acquire(self, email: str, idle_timeout: int = 10):
        """
        Raises:
            AcquireError
        """
        device = await db.table("devices").get(self.udid).run()
        if not device:
            raise AcquireError("device not exist")
        if not device.get('sources'):  # 设备离线
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
        now = time_now()
        await self.update({
            "userId": email,
            "usingBeganAt": now,
            "lastActivatedAt": now,
            "idleTimeout": idle_timeout,
        })
        self.check_background(device)  # release when idleTimeout

    def _next_check_after(self, device) -> int:
        print("ACT", device['lastActivatedAt'], device['idleTimeout'], "NOW",
              time_now())
        time_deadline = device['lastActivatedAt'] + datetime.timedelta(
            seconds=device['idleTimeout'])
        delta = time_deadline - time_now()
        return max(0, int(delta.total_seconds()))

    def check_background(self, device: dict):
        began_at = device['usingBeganAt']
        after_seconds = self._next_check_after(device) + 3
        logger.info("First check after %d seconds", after_seconds)
        IOLoop.current().spawn_callback(self._check, began_at, after_seconds)

    async def _check(self, began_at: datetime.datetime.time,
                     idle_timeout: int):
        """ when time_now > lastActivatedAt + idleTimeout, release device """
        await gen.sleep(idle_timeout)
        min_timedelta = datetime.timedelta(seconds=1)

        device = await db.table("devices").get(self.udid).run()
        # 当开始使用时间不一致时，说明设备已经换人了
        if began_at - device['usingBeganAt'] > min_timedelta:
            logger.info("_check different began_at %s != %s",
                        device['usingBeganAt'], began_at)
            return

        # calculate left time
        left_seconds = self._next_check_after(device)
        logger.info("Left seconds: %s", left_seconds)
        if left_seconds == 0:
            await self.release(device['userId'])
            return

        # 等待进入下一次检查
        IOLoop.current().add_callback(self._check, began_at, left_seconds + 3)

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
        # 设备先要冷却一下(Provider清理并检查设备)
        await self.update({"using": False, "userId": None, "colding": True})
        source = device2source(device)
        if not source:  # 设备离线了
            return

        async def cold_device():
            from tornado.httpclient import AsyncHTTPClient, HTTPRequest
            http_client = AsyncHTTPClient()
            secret = source.get('secret', '')
            url = source['url'] + "/" + device['udid'] + "?secret=" + secret
            request = HTTPRequest(url, method="DELETE")
            await http_client.fetch(request)

        IOLoop.current().add_callback(cold_device)


def device2source(device: dict):
    sources = device.get('sources', {}).values()
    for s in sorted(sources, key=lambda v: v['priority'], reverse=True):
        return s


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
