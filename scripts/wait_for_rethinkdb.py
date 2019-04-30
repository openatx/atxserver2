#!/use/bin/env python
# coding: utf-8
#

import os
import sys
import time

from rethinkdb import r


deadline = time.time() + 10
while time.time() < deadline:
    try:
        conn = r.connect(os.environ.get("RDB_HOST", "localhost"))
        print("RethinkDB is running")
        res = r.db_list().run(conn)
        assert isinstance(res, list)
        sys.exit(0)
    except Exception as e:
        time.sleep(.2)
        #print(e, end="")

sys.exit("RethinkDB is not started")
