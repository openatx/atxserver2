# coding: utf-8
#
# handlers for atxslave
#

import json
import uuid
from tornado.ioloop import IOLoop
from logzero import logger

from rethinkdb import r
from ..database import db, time_now
from .base import BaseWebSocketHandler


class ProviderHeartbeatWSHandler(BaseWebSocketHandler):
    """ monitor device online or offline """

    providers = {}

    @staticmethod
    async def release(source_id, udid):
        """
        Release device when finished using
        """
        ws = ProviderHeartbeatWSHandler.providers.get(source_id)
        if not ws:
            return
        await ws.write_message({"command": "release", "udid": udid})

    def initialize(self):
        self._id = None
        self._owner = None
        self._info = None

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

        {"name": "ccddqq",
         "url": "http://xlksdf.com",
         "secret": "xxxxxx....",
         "owner": "someone@domain.com"}
        """
        assert "name" in req
        assert "url" in req
        assert "secret" in req
        assert "priority" in req
        # assert "owner" in req

        self._id = req['id'] = str(uuid.uuid1())
        self._owner = req.get('owner', "")
        self._info = req

        # hotfix for old provider
        if self._owner == "nobody@nobody.io":
            self._owner = ""
        self.write_message(json.dumps({
            "success": True,
            "id": self._id,
        }))
        self.providers[self._id] = self # providers is global variable
        logger.debug("A new provider is online " + req['name'] + " ID:" +
                     self._id)


    async def _on_update(self, req):
        """
        {
            "command": "update",
            "udid": "xxx12312312",
            "platform": "android",
            "provider": {
                "deviceAddress": "....",
                "remoteConnectAddress": "....", # 远程连接用
            },
            "properties": {
                {...},
            }
        }
        """
        updates = req.copy()
        udid = updates['udid']
        assert isinstance(udid, str)

        # add owner
        updates['owner'] = self._owner

        source = updates.pop('provider', {})
        if source is None:
            # remove source
            await db.table("devices").get(udid).replace(lambda q: q.without(
                {"sources": {
                    self._id: True
                }}))
        else:
            # one device may contains many sources
            source.update(self._info)
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
        # logger.info("receive message: %s", message)

    def on_close(self):
        logger.info("websocket closed: %s", self.request.remote_ip)
        self.providers.pop(self._id, None)

        async def remove_source():
            def inner(q):
                return q.without({"sources": {self._id: True}})

            #
            await db.table("devices").replace(inner)

            # set using to false if there is no sources
            filter_rule = r.row["sources"].default({}).keys().count().eq(0)
            await db.table("devices").filter(filter_rule).update({
                "using": False,
                "colding": False,
            }) # yapf: disable

        IOLoop.current().add_callback(remove_source)
