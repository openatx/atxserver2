# coding: utf-8
#

from tornado.web import authenticated
import rethinkdb as r

from ..database import db, time_now
from .base import BaseRequestHandler


class UserHandler(BaseRequestHandler):
    def get(self):
        self.render("user.html")


class APIUserHandler(BaseRequestHandler):
    async def get(self):
        """
        Return:
            dict
        
        For example
        {
            "createdAt": "2019-02-18T11:06:53.621000+08:00",
            "email": "fa@anonymous.com",
            "lastLoggedInAt": "2019-02-21T20:31:29.639000+08:00",
            "secretKey": "S:15cc65f5-3eeb-4fec-8131-355ad03653d4",
            "username": "fa",
            "groups": [
                {
                    "auth": {
                        "admin": true
                    },
                    "creator": "fa@anonymous.com",
                    "id": "1",
                    "name": "g4"
                }
            ]
        }
        """
        user_email = self.current_user.email

        def merge_function(v):
            return {"auth": v.get_field("members")[user_email]}

        cursor = await db.run(
            db.table("groups").reql.filter(
                r.row.has_fields({"members": {
                    user_email: True,
                }})).merge(merge_function).without("members"))
        groups = []
        while await cursor.fetch_next():
            groups.append(await cursor.next())
        user = self.current_user.copy()
        user["groups"] = groups
        self.write_json(user)

    def put(self):
        """ update token """
        pass


class UserGroupCreateHandler(BaseRequestHandler):
    def get(self):
        self.render("group_create.html")


class APIUserGroupHandler(BaseRequestHandler):
    def get(self):
        # db.table("groups").reql.filter()
        pass

    async def post(self):
        id = self.get_argument("id")
        name = self.get_argument("name")
        ret = await db.run(
            db.table("groups").reql.insert({
                "id": id,
                "name": name,
                "createdAt": time_now(),
                "creator": self.current_user.email,
                "members": {
                    self.current_user.email: {
                        "admin": True,
                    }
                }
            }))
        print(ret)
        self.write_json(ret)
