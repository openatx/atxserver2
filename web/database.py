# coding: utf-8
#

import datetime
import json

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
    __tables = {
        "devices": {
            "name": "devices",
            "primary_key": "udid",
        },
        "users": {
            "name": "users",
            "primary_key": "email",
        }
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

        def safe_run(rsql):
            try:
                return rsql.run(conn)
            except r.RqlRuntimeError:
                return False

        # init databases here
        safe_run(r.db_create(self.__dbname))

        rdb = r.db(self.__dbname)
        for tbl in self.__tables.values():
            table_name = tbl['name']
            primary_key = tbl.get('primary_key', 'id')
            safe_run(rdb.table_create(table_name, primary_key=primary_key))

        # reset database
        safe_run(rdb.table("devices").update({"present": False}))
        safe_run(rdb.table("devices").replace(lambda q: q.without("sources")))

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
        pkey = self.__tables.get(name, {}).get("primary_key")
        return DBTable(self, name, primary_key=pkey)

    def __getattr__(self, name):
        """
        use this magic function, it is possible to write code like this

            user = await db.users.get("codeskyblue@gmail.com")
        """
        if name not in self.__tables:
            raise AttributeError("database table not exist", name)
        tbl = self.__tables[name]
        return DBTable(self, tbl['name'], primary_key=tbl.get('primary_key'))


class DBTable(object):
    def __init__(self, db, table_name: str, primary_key='id'):
        self.__db = db
        self.__table_name = table_name
        self.__pkey = primary_key

    @property
    def _table(self):
        return r.table(self.__table_name)

    @property
    def reql(self):
        return r.table(self.__table_name)

    def _run(self, rsql):
        return self.__db.run(rsql)

    async def run(self, f):
        rsql = f(self._table)
        return await self._run(rsql)

    async def update(self, data: dict, id=None):
        """
        Update data into database

        Args:
            data: dict
            id: primary_key id, if not specified, update will apply to all

        Returns:
            dict of updated details
            {
                "deleted": 0 ,
                "errors": 0 ,
                "inserted": 0 ,
                "replaced": 0 ,
                "skipped": 0 ,
                "unchanged": 0
            }
        """
        rsql = self._table
        if id:
            rsql = rsql.get(id)
        ret = await self._run(rsql.update(data))
        return ret

    async def save(self, data: dict, id=None):
        """
        Update or insert data into database

        Returns:
            dict, id will be in it
        """
        data = data.copy()
        if id:
            data[self.__pkey] = id

        # update if has primary_key
        if self.__pkey in data:
            id = data[self.__pkey]
            ret = await self._run(self._table.get(id).update(data))
            print(ret)
            if not ret['skipped']:
                ret['id'] = id
                return ret

        # add some data
        data['createdAt'] = time_now()

        ret = await self._run(self._table.insert(data))
        assert ret['errors'] == 0

        if "generated_keys" in ret:
            ret['id'] = ret["generated_keys"][0]
            return ret

        ret['id'] = id
        return ret

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

    async def count(self) -> int:
        return await self._run(self._table.count())

    async def delete(self, id):
        return await self._run(self._table.delete(id))

    async def watch(self):
        """ return (conn, feed) """
        conn = await self.__db.connection()
        feed = await r.table(self.__table_name).changes().run(conn)
        return conn, feed


db = DB(
    settings.RDB_DBNAME,
    host=settings.RDB_HOST,
    port=settings.RDB_PORT,
    user=settings.RDB_USER,
    password=settings.RDB_PASSWD)
