# coding: utf-8
#

import os

RDB_HOST = os.getenv("RDB_HOST") or "localhost"
RDB_PORT = int(os.getenv("RDB_PORT") or "28015")
RDB_USER = os.getenv("RDB_USER") or "admin"
RDB_PASSWD = os.getenv("RDB_PASSWD") or None
RDB_DBNAME = os.getenv("RDB_NAME") or "atxserver2"
