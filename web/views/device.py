# coding: utf-8
#

import json

from logzero import logger
from tornado.web import authenticated, RequestHandler

from ..database import db, jsondate_loads, time_now
from ..utils import jsondate_dumps
from .base import BaseRequestHandler, BaseWebSocketHandler, AuthRequestHandler


class DeviceItemHandler(BaseRequestHandler):
    async def put(self, id):
        pass

    async def get_json(self, id):
        data = await db.table("records").get(id)
        self.write_json({
            "success": True,
            "data": data,
        })

    async def get_html(self, id):
        self.render("record.html")


class DeviceListHandler(BaseRequestHandler):
    """ Device List will show in first page """

    async def get(self):
        """ get data from database """
        if self.get_argument('json', None) is not None:
            self.write_json({
                "success": True,
                "data": {
                    "devices": await db.table("devices").get_all(limit=50, desc="createdAt"),
                    "count": await db.table("devices").count(),
                }
            })  # yapf: disable
            return
        self.render("index.html")

    async def post(self):
        """ add data into database """
        data = jsondate_loads(self.request.body)
        id = await db.table("devices").save(data)
        self.write_json({"id": id, "data": data})


class DeviceChangesWSHandler(BaseWebSocketHandler):
    def write_json(self, data):
        self.ws_connection.write_message(jsondate_dumps(data))

    async def open(self):
        self.__opened = True
        conn, feed = await db.table("devices").watch()
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


class DeviceControlHandler(AuthRequestHandler):
    def get(self, udid):
        pass


class OccupyError(Exception):
    pass


async def occupy_device(email: str, udid: str):
    device = await db.device.get(udid)
    if not device:
        raise OccupyError("device not exist")
    if not device.get('present'):
        raise OccupyError("device absent")
    if device.get('using'):
        if device.get('userId') == email:
            # already used by ..{email}
            return
        raise OccupyError("device busy")

    ret = await db.device.update({"using": True}, udid)
    if ret['skipped'] == 1:
        raise OccupyError(
            "not fast enough, device have been taken from others")
    await db.device.update({"userId": email, "usingBebanAt": time_now()}, udid)


class DeviceBookWSHandler(BaseWebSocketHandler):
    """ 连接成功时占用，断开时释放设备 """

    async def open(self, udid):
        if not self.current_user:
            self.write_message("need to login")
            self.close()
            return

        email = self.current_user.email
        try:
            await occupy_device(email, udid)
        except OccupyError as e:
            self.write_message(str(e))
            self.close()
            return

        self.write_message("device is yours")
