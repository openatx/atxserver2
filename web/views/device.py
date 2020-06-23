# coding: utf-8
#

import datetime
import json
import urllib
from functools import wraps
from typing import Union

import rethinkdb as rdb
import tornado.websocket
from logzero import logger
from rethinkdb import r
from tornado import gen
from tornado.httpclient import AsyncHTTPClient, HTTPRequest
from tornado.ioloop import IOLoop
from tornado.web import HTTPError, authenticated

from ..database import db, time_now
from ..libs import jsondate
from ..version import __version__
from .base import (AuthRequestHandler, BaseRequestHandler,
                   BaseWebSocketHandler, CorsMixin)


class AcquireError(Exception):
    pass


class ReleaseError(Exception):
    pass


class APIDeviceListHandler(CorsMixin, BaseRequestHandler):
    async def get(self):
        def filter_accessible(v):  # filter out private device
            groups = self.current_user.get("groups", {}).keys()
            groups = list(groups) + [self.current_user.email, ""
                                     ]  # include user-private device
            return r.expr(groups).contains(v['owner'].default(""))

        reql = db.table_devices.without("sources", "source")
        if not self.current_user.admin:
            reql = reql.filter(filter_accessible)

        if self.get_argument("platform", ""):
            reql = reql.filter({"platform": self.get_argument("platform")})
        if self.get_argument("usable", None):  # 只查找能用的设备
            reql = reql.filter({
                "using": False,
                "colding": False,
                "present": True
            })
        if self.get_argument("present", None):
            reql = reql.filter(
                {"present": self.get_argument("present") == "true"})

        reql = reql.order_by(r.desc("createdAt"))
        devices = await reql.all()

        if self.get_argument("present", ""):
            present = self.get_argument("present") == "true"
            devices = [d for d in devices if d['present'] == present]

        self.write_json({
            "success": True,
            "devices": devices,
            "count": await db.table_devices.count(),
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
                "description": "Device activated time updated"
            })
        else:
            self.set_status(400)
            self.write_json({
                "success": False,
                "description": "Device is not owned by you"
            })


def catch_error_wraps(*errors):
    """ write 400 if error raises """

    def decorator(fn):
        @wraps(fn)
        async def inner(self, *args, **kwargs):
            try:
                print(errors)
                return await fn(self, *args, **kwargs)
            except errors as e:
                self.set_status(400)  # bad request
                self.write_json({
                    "success": False,
                    "description": "error: %s" % e,
                })

        return inner

    return decorator


class APIDeviceHandler(CorsMixin, BaseRequestHandler):
    @catch_error_wraps(rdb.errors.ReqlNonExistenceError)
    async def get(self, udid):
        data = await db.table("devices").get(udid).without("sources").run()
        self.write_json({
            "success": True,
            "device": data,
        })

    @catch_error_wraps(rdb.errors.ReqlNonExistenceError)
    async def put(self, udid):
        if not self.current_user.admin:
            raise RuntimeError("Update requires admin")

        props = self.get_payload()
        await db.table("devices").get(udid).update({
            "department": props['department'],
        })
        self.write_json({"success": True, "description": "updated"})


class APIDevicePropertiesHandler(CorsMixin, BaseRequestHandler):
    @catch_error_wraps(rdb.errors.ReqlNonExistenceError)
    async def get(self, udid):
        data = await db.table("devices").get(udid).pluck("udid",
                                                         "properties").run()
        self.write_json({
            "success": True,
            "data": data,
        })

    @catch_error_wraps(rdb.errors.ReqlNonExistenceError, RuntimeError)
    async def put(self, udid):
        if not self.current_user.admin:
            raise RuntimeError("Update property requires admin")

        props = self.get_payload()
        await db.table("devices").get(udid).update({
            "properties": props,
        })
        self.write_json({"success": True, "description": "Propery updated"})


class APIUserDeviceHandler(CorsMixin, AuthRequestHandler):
    """ device Acquire and Release """

    async def get_device(self, udid):
        data = await db.table("devices").get(udid).run()
        if not data:
            self.set_status(400)  # bad request
            self.write_json({
                "success": False,
                "description": "device not found " + udid,
            })
            return
        if not self.current_user.admin and \
                data.get('userId') != self.current_user.email:
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
            "device": data,
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
        idle_timeout = data.get('idleTimeout', 600)  # 默认10分钟
        email = self.current_user.email

        # Admin: change user email
        if data.get("email"):
            if not self.current_user.admin:
                raise HTTPError(403)
            email = data.get('email')

        if email != self.current_user.email:
            logger.info("Device %s if acquired by %s for %s", udid,
                        self.current_user.email, email)

        try:
            await D(udid).acquire(email, idle_timeout)
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
            email = "" if self.current_user.admin else self.current_user.email
            await D(udid).release(email)
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
        self.render("index.html", version=__version__)


class DeviceChangesWSHandler(BaseWebSocketHandler):
    async def write_json(self, data: dict):
        await self.write_message(jsondate.dumps(data))
        # try:
        #     self.write_message(jsondate.dumps(data))
        # except tornado.websocket.WebSocketClosedError:
        #     self.__opened = False

    async def send_feed(self):
        def filter_accessible(v):  # filter out private device
            groups = self.current_user.get("groups", {}).keys()
            groups = list(groups) + [self.current_user.email, ""]
            return r.expr(groups).contains(v['owner'].default(""))

        reql = db.table_devices
        if not self.current_user.admin:
            reql = reql.filter(filter_accessible)

        conn, feed = await reql.watch()
        with conn:
            while await feed.fetch_next():
                if not self.__opened:
                    break
                data = await feed.next()
                await self.write_json({
                    "event": "insert" if data['old_val'] is None else 'update',
                    "data": data['new_val'],
                })  # yapf: disable

    async def open(self):
        self.__opened = True
        IOLoop.current().add_callback(self.send_feed)

    def on_message(self, msg):
        # logger.debug("receive message %s", msg)
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

    async def acquire(self, email: str, idle_timeout: int = 20 * 60):
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
        self.release_until_idle()  # release when idleTimeout

    def release_until_idle(self):
        async def first_check():
            device = await db.table("devices").get(self.udid).run()
            began_at = device['usingBeganAt']
            after_seconds = self._next_check_after(device) + 3
            logger.info("First check after %d seconds", after_seconds)
            IOLoop.current().add_callback(self._check, began_at, after_seconds)

        IOLoop.current().spawn_callback(first_check)

    def _next_check_after(self, device) -> int:
        time_deadline = device['lastActivatedAt'] + datetime.timedelta(
            seconds=device['idleTimeout'])
        delta = time_deadline - time_now()
        return max(0, int(delta.total_seconds()))

    async def _check(self, began_at: datetime.datetime.time,
                     idle_timeout: int):
        """ when time_now > lastActivatedAt + idleTimeout, release device """
        await gen.sleep(idle_timeout)

        device = await db.table("devices").get(self.udid).run()
        # 当开始使用时间不一致时，说明设备已经换人了
        if began_at != device['usingBeganAt']:
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

    async def release(self, email: Union[str, None]):
        """
        Admin can provider empty email

        Raises:
            ReleaseError
        """
        device = await db.table("devices").get(self.udid).run()
        if not device:
            raise ReleaseError("device not exist")
        if email and device.get('userId') != email:
            raise ReleaseError("device is not owned by you")

        if not device.get("using"):  # already released
            return

        # Update database
        await self.update({
            "using": False,
            "userId": None,
            "colding": True,
            "usingDuration": r.row["usingDuration"].default(0).add(r.now().sub(r.row["usingBeganAt"]))
        }) # yapf: disable

        # 设备先要冷却一下(Provider清理并检查设备)
        source = device2source(device)
        if not source:  # 设备离线了
            return
        
        async def cold_device():
            from tornado.httpclient import HTTPError
            from tornado.httpclient import AsyncHTTPClient, HTTPRequest
            http_client = AsyncHTTPClient()
            secret = source.get('secret', '')
            if not source.get('url'):
                await self.update({"colding": False})
                return
            
            source_id = source.get("id")
            from .provider import ProviderHeartbeatWSHandler
            await ProviderHeartbeatWSHandler.release(source_id, device['udid'])

            try:
                url = source['url'] + "/cold?" + urllib.parse.urlencode(
                    dict(udid=device['udid'], secret=secret))
                request = HTTPRequest(url, method="POST", body='')
                await http_client.fetch(request)
            except HTTPError as e:
                logger.error("device [%s] release error: %s", self.udid, e)
                await self.update({"colding": False})

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
