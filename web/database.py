# coding: utf-8
#

import datetime
import json
import os

import rethinkdb as r
from logzero import logger

from . import settings


def time_now():
    return datetime.datetime.now(r.make_timezone("+08:00"))


def _json_decoder(d):
    for key, val in d.items():
        if val == '':
            continue
        try:
            obj = datetime.datetime.fromisoformat(val)
            d[key] = obj.astimezone(r.make_timezone("+08:00"))
        except (ValueError, TypeError):
            continue

    return d


def jsondate_loads(s):
    return json.loads(s, object_hook=_json_decoder)


class DB(object):
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

        def safe_run(rsql):
            try:
                return rsql.run(conn)
            except r.RqlRuntimeError:
                return False

        # init databases here
        safe_run(r.db_create(self.__dbname))
        rdb = r.db(self.__dbname)
        safe_run(rdb.table_create("devices"))

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
        Returns
            DBTable
        """
        return DBTable(self, name)

    @property
    def device(self):
        return self.table("devices")


class DBTable(object):
    def __init__(self, db, table_name: str, primary_key='id'):
        self.__db = db
        self.__table_name = table_name
        self.__pkey = primary_key

    @property
    def _table(self):
        return r.table(self.__table_name)

    def _run(self, rsql):
        return self.__db.run(rsql)

    async def save(self, data: dict, id=None):
        """
        Update or insert data into database

        Returns:
            id
        """
        data = data.copy()
        if id:
            data[self.__pkey] = id

        # update if has primary_key
        if self.__pkey in data:
            id = data[self.__pkey]
            ret = await self._run(self._table.get(id).update(data))
            if not ret['skipped']:
                return id

        # add some data
        data['createdAt'] = time_now()

        ret = await self._run(self._table.insert(data))
        assert ret['errors'] == 0

        if "generated_keys" in ret:
            return ret["generated_keys"][0]

        return data[self.__pkey]

    async def get(self, id):
        return await self._run(self._table.get(id))

    async def get_all(self, limit=None, desc=None, rsql_hook=None):
        """
        return list of result
        """
        with await self.__db.connection() as conn:
            query = self._table
            if desc:
                query = query.order_by(r.desc(desc))
            if rsql_hook:
                query = rsql_hook(query)
            if limit:
                query = query.limit(limit)
            cursor = await query.run(conn)
            if isinstance(cursor, (list, tuple)):
                return cursor

            result = []
            while await cursor.fetch_next():
                result.append(await cursor.next())
            return result

    async def delete(self, id):
        return await self._run(self._table.delete(id))

    async def watch(self):
        """ return (conn, feed) """
        conn = await self.__db.connection()
        feed = await r.table(self.__table_name).changes().run(conn)
        return conn, feed

    async def update(self, data: dict, id=None):
        rsql = self._table
        if id:
            rsql = rsql.get(id)
        return await rsql.update(data)




db = DB(
    settings.RDB_DBNAME,
    host=settings.RDB_HOST,
    port=settings.RDB_PORT,
    user=settings.RDB_USER,
    password=settings.RDB_PASSWD)
