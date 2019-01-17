# coding: utf-8
#

import json

import tornado.websocket
from logzero import logger
from tornado.web import authenticated

from ..database import db, jsondate_loads
from ..utils import jsondate_dumps
from .base import BaseRequestHandler


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

    @authenticated
    async def get(self):
        """ get data from database """
        if self.get_argument('json', None) is not None:
            self.write_json({
                "success": True,
                "data": await db.table("devices").get_all(limit=50, desc="createdAt"),
            }) # yapf: disable
            return
        self.render("index.html")

    async def post(self):
        """ add data into database """
        data = jsondate_loads(self.request.body)
        id = await db.table("devices").save(data)
        self.write_json({"id": id, "data": data})



class DeviceChangesWSHandler(tornado.websocket.WebSocketHandler):
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
                }) # yapf: disable

    def on_message(self, msg):
        logger.debug("receive message %s", msg)
        pass

    def on_close(self):
        self.__opened = False
        print("Websocket closed")


class DeviceHeartbeatWSHandler(tornado.websocket.WebSocketHandler):
    """ monitor device online or offline """
    def check_origin(self, origin):
        return True

    def open(self):
        """
        id: xxxx,
        name: xxxx,
        bindAddress: "10.0.0.1:6477",
        """
        logger.info("new websocket connected: %s", self.request.remote_ip)
        pass
    
    def _on_ping(self, req):
        self.write_message("pong")

    def _on_handshake(self, req):
        self.write_message("you are online")

    def on_message(self, message):
        req = json.loads(message)
        assert 'command' in req

        getattr(self, "_on_"+req['command'])(req)

        """
        {"command": "ping"} // ping, update
        // command: "updateDevices", data: []

        devices: [{
            "udid": "xxxxsdfasdf",
            "present": true,
        }, {
            "udid": "xxlksjdfljsf",
            "properties": {
                "version": "1.2.0",
            },
            "present": false,
        }]
        """
        logger.info("receive message: %s", message)
    
    def on_close(self):
        logger.info("websocket closed: %s", self.request.remote_ip)
        pass
