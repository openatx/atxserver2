# coding: utf-8
#

import datetime
import json

from rethinkdb import r
from logzero import logger

from . import settings
from .libs import jsondate


def time_now():
    return datetime.datetime.now(r.make_timezone("+08:00"))


class DB(object):
    __tables = {
        "devices": {
            "name": "devices",
            "primary_key": "udid",
        },
        "users": {
            "name": "users",
            "primary_key": "email",
        },
        "groups": {
            "name": "groups",
        },
    }

    def __init__(self, db='demo', **kwargs):
        self.__connect_kwargs = kwargs
        self.__dbname = db
        self.__is_setup = False

    def setup(self):
        """ setup must be called before everything """
        if self.__is_setup:
            return
        self.__is_setup = True

        conn = r.connect(**self.__connect_kwargs)

        def safe_run(rsql, show_error=False):
            try:
                return rsql.run(conn)
            except r.RqlRuntimeError as e:
                if show_error:
                    logger.warning("safe_run rsql:%s, error:%s", rsql, e)
                return False

        # init databases here
        safe_run(r.db_create(self.__dbname))

        rdb = r.db(self.__dbname)
        for tbl in self.__tables.values():
            table_name = tbl['name']
            primary_key = tbl.get('primary_key', 'id')
            safe_run(rdb.table_create(table_name, primary_key=primary_key))

        # reset database
        safe_run(rdb.table("users").index_create("token"))
        safe_run(rdb.table("devices").replace(lambda q: q.without("sources")))

        # reload add idle check functions
        from .views.device import D  # must import in here

        devices = safe_run(
            rdb.table("devices").filter({
                "using": True
            }).pluck("udid"), show_error=True)

        if devices:
            for d in devices:
                logger.debug("Device: %s is in using state", d['udid'])
                D(d['udid']).release_until_idle()

        r.set_loop_type("tornado")

    async def connection(self):
        """ TODO(ssx): add pool support """
        return await r.connect(db=self.__dbname, **self.__connect_kwargs)

    async def run(self, rsql):
        c = await self.connection()
        try:
            return await rsql.run(c)
        finally:
            c.close()

    def table(self, name):
        """
        Returns:
            TableHelper
        """
        pkey = self.__tables.get(name, {}).get("primary_key")
        return TableHelper(self, r.table(name), pkey=pkey)

    @property
    def table_devices(self):
        def _fn(v):
            return {
                "present": v.get_field("sources").default({}).count().gt(0)
            }

        return self.table("devices").merge(_fn)

    # def tableof(self, name):
    #     """
    #     Returns:
    #         DBTable
    #     """
    #     pkey = self.__tables.get(name, {}).get("primary_key")
    #     return DBTable(self, name, primary_key=pkey)

    # def __getattr__(self, name):
    #     """
    #     use this magic function, it is possible to write code like this

    #         user = await db.users.get("codeskyblue@gmail.com")
    #     """
    #     if name not in self.__tables:
    #         raise AttributeError("database table not exist", name)
    #     tbl = self.__tables[name]
    #     return DBTable(self, tbl['name'], primary_key=tbl.get('primary_key'))


class TableHelper(object):
    """
    简化rethinkdb的代码

    From
        await with r.connect() as conn:
            await conn.run(r.table("users").delete())

    To
        await db.table("users").delete()

    More simple examples:
        ret = await db.table("users").filter({"present": True}).delete()
        ret = await db.table("users").insert({"name": "hello world"})
    """

    def __init__(self, db, reql, pkey='id'):
        self.__db = db
        self.__reql = reql
        self.__pkey = pkey

    @property
    def primary_key(self):
        return self.__pkey or 'id'

    def clone(self, db=None, reql=None, pkey=None):
        db = db or self.__db
        reql = reql or self.__reql
        pkey = pkey or self.primary_key
        return TableHelper(db, reql, pkey)

    def filter(self, *args, **kwargs):
        reql = self.__reql.filter(*args, **kwargs)
        return self.clone(reql=reql)

    def get(self, *args, **kwargs):
        reql = self.__reql.get(*args, **kwargs)
        return self.clone(reql=reql)

    def update(self, *args, **kwargs):
        reql = self.__reql.update(*args, **kwargs)
        return self.__db.run(reql)

    def insert(self, *args, **kwargs):
        reql = self.__reql.insert(*args, **kwargs)
        return self.__db.run(reql)

    def delete(self, *args, **kwargs):
        reql = self.__reql.delete(*args, **kwargs)
        return self.__db.run(reql)

    def replace(self, *args, **kwargs):
        reql = self.__reql.replace(*args, **kwargs)
        return self.__db.run(reql)

    def count(self):
        reql = self.__reql.count()
        return self.__db.run(reql)

    def run(self):
        return self.__db.run(self.__reql)

    async def watch(self):
        """ return (conn, feed) """
        conn = await self.__db.connection()
        feed = await self.__reql.changes().run(conn)
        return conn, feed

    async def all(self):
        """Retrive all the matches

        Returns:
            list of item
        """
        with await self.__db.connection() as conn:
            cursor = await self.__reql.run(conn)
            if isinstance(cursor, (list, tuple)):
                return cursor

            results = []
            while await cursor.fetch_next():
                results.append(await cursor.next())
            return results

    async def save(self, data: dict, id=None) -> dict:
        """Update when exists or insert it

        Returns:
            dict which will contains "id"
        """
        data = data.copy()
        if id:
            data[self.primary_key] = id

        # update if has primary_key
        if self.primary_key in data:
            id = data[self.primary_key]
            ret = await self.get(id).update(data)
            if not ret['skipped']:
                ret['id'] = id
                return ret

        # add some data
        data['createdAt'] = time_now()

        ret = await self.insert(data)
        assert ret['errors'] == 0

        if "generated_keys" in ret:
            ret['id'] = ret["generated_keys"][0]
            return ret

        ret['id'] = id
        return ret

    def __getattr__(self, key):
        if hasattr(self.__reql, key):

            def inner(*args, **kwargs):
                reql = getattr(self.__reql, key)(*args, **kwargs)
                return self.clone(reql=reql)

            return inner
        raise AttributeError("No such attribute " + key)


db = DB(
    settings.RDB_DBNAME,
    host=settings.RDB_HOST,
    port=settings.RDB_PORT,
    user=settings.RDB_USER,
    password=settings.RDB_PASSWD)
