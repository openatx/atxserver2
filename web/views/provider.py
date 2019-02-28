# coding: utf-8
#
# handlers for atxslave
#

import json
import uuid
from tornado.ioloop import IOLoop
from logzero import logger

import rethinkdb as r
from ..database import db, time_now
from .base import BaseWebSocketHandler


class ProviderHeartbeatWSHandler(BaseWebSocketHandler):
    """ monitor device online or offline """

    providers = {}

    @staticmethod
    async def release(udid: str):
        """
        Release device when finished using
        """
        device = await db.table("devices").get(udid).run()
        if not device:
            return

        for sid in device.get('sources', {}).keys():
            ws = ProviderHeartbeatWSHandler.providers.get(sid)
            if not ws:
                continue
            ws.write_message({"command": "release", "udid": udid})
            break
        else:
            logger.warning("device %s source is missing", udid)

    def initialize(self):
        self._owner = None
        self._id = None
        self._info = None
        self._priority = 0

    def open(self):
        """
        id: xxxx,
        name: xxxx,
        bindAddress: "10.0.0.1:6477",
        """
        logger.info("new websocket connected: %s", self.request.remote_ip)
        # self.providers[]
        pass

    async def _on_ping(self, req):
        """
        {"command": "ping"}
        """
        self.write_message("pong")

    async def _on_handshake(self, req: dict):
        """
        identify slave self

        {"command": "handshake",
         "name": "ccddqq",
         "owner": "someone@domain.com"}
        """
        assert "name" in req
        assert "priority" in req
        req.pop("command", None)
        self._id = req['id'] = str(uuid.uuid1())
        self._info = req
        self._priority = req['priority']
        self.write_message("you are online " + req['name'])

    async def _on_update(self, req):
        """
        {
            "command": "update",
            "udid": "xxx12312312",
            "platform": "android",
            "present": true,
            "provider": {
                "deviceAddress": "....",
                "remoteConnectAddress": "....", # 远程连接用
            },
            "properties": {
                {...},
            }
        }
        """
        import pprint
        pprint.pprint(req)

        updates = req.copy()
        udid = updates['udid']
        assert isinstance(udid, str)

        source = updates.pop('provider', None)
        if source is None:
            # remove source
            await db.table("devices").get(udid).replace(lambda q: q.without(
                {"sources": {
                    self._id: True
                }}))
        else:
            # one device may contains many sources
            source['priority'] = self._priority
            updates['sources'] = {
                self._id: source,
            }
        updates['updatedAt'] = time_now()
        await db.table("devices").save(updates, udid)

    async def on_message(self, message):
        req = json.loads(message)
        assert 'command' in req
        command = req.pop('command')
        await getattr(self, "_on_" + command)(req)
        """
        {"command": "ping"} // ping, update
        """
        logger.info("receive message: %s", message)

    def on_close(self):
        logger.info("websocket closed: %s", self.request.remote_ip)

        async def remove_source():
            def inner(q):
                return q.without({"sources": {self._id: True}})

            #
            await db.table("devices").replace(inner)

            # set present,using to false if there is no sources
            filter_rule = r.row["sources"].default({}).keys().count().eq(0)
            await db.table("devices").filter(filter_rule).update({
                "present": False,
                "using": False,
            }) # yapf: disable

        IOLoop.current().add_callback(remove_source)
