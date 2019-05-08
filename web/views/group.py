# coding: utf-8
#

from rethinkdb import r

from ..database import db, time_now
from .base import AuthRequestHandler, AdminRequestHandler

_GROUP_ADMIN = 2
_GROUP_USER = 1


class UserGroupCreateHandler(AuthRequestHandler):
    def get(self):
        self.render("group_create.html")


class APIGroupUserListHandler(AuthRequestHandler):
    """ list group users """

    async def get(self, group_id):
        users = await db.table("users").has_fields(dict(groups=group_id)).without("groups").all() # yapf: disable
        self.write_json({"success": True, "data": users})


class APIUserGroupHandler(AuthRequestHandler):
    pass


class APIUserGroupListHandler(AuthRequestHandler):
    """ Create|Leave group """

    # def get(self):
    #     self.write_json(self.current_user)
    async def post(self):
        id = self.get_argument("id")
        name = self.get_argument("name")
        if id.find("@") != -1:
            self.set_status(400)  # bad request
            self.write_json({
                "success": False,
                "description": "GroupID Should not contains '@'"
            })
            return

        ret = await db.table("groups").insert({
            "id": id,
            "name": name,
            "createdAt": time_now(),
            "creator": self.current_user.email,
        }) # yapf: disable

        if ret['inserted']:
            await db.table("users").get(self.current_user.email).update(
                dict(groups={id: _GROUP_ADMIN}))
            self.write_json({
                "success": True,
                "description": "Group successfully created"
            })
        else:
            self.set_status(400)  # bad request
            self.write_json({
                "success": False,
                "description": "GroupID Duplicated error, ID=" + id
            })
