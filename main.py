# coding: utf-8
#

import argparse
import socket
from pprint import pprint

import tornado.ioloop
from logzero import logger
from rethinkdb import r
from tornado.httpserver import HTTPServer
from tornado.log import enable_pretty_logging

from web.database import db
from web.entry import make_app
from web.views import OpenIdLoginHandler, SimpleLoginHandler


def machine_ip():
    """ return current machine ip """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    try:
        return s.getsockname()[0]
    finally:
        s.close()


def main():
    _auth_handlers = {
        "simple": SimpleLoginHandler,
        "openid": OpenIdLoginHandler,
    }

    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    # yapf: disable
    parser.add_argument('-p', '--port', type=int,
                        default=4000, help='listen port')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='open debug log, and open hot reload')
    parser.add_argument('--auth', type=str, default='simple',
                        choices=_auth_handlers.keys(), help='authentication method')
    parser.add_argument("--no-xheaders", action="store_true", help="disable support for X-Real-Ip/X-Forwarded-For")
    parser.add_argument(
        '--auth-conf-file', type=argparse.FileType('r'), help='authentication config file')
    # yapf: enable

    args = parser.parse_args()
    print(args)
    enable_pretty_logging()

    db.setup()

    ioloop = tornado.ioloop.IOLoop.current()

    # TODO(ssx): for debug use
    # async def dbtest():
    #     items = await db.table("devices").get_all(
    #         limit=2, rsql_hook=lambda q: q.order_by(r.desc("createdAt")))
    #     for item in items:
    #         pprint(item)

    # ioloop.spawn_callback(dbtest)

    login_handler = _auth_handlers[args.auth]
    app = make_app(login_handler, debug=args.debug)
    server = HTTPServer(app, xheaders=not args.no_xheaders)
    server.listen(args.port)
    logger.info("listen on port http://%s:%d", machine_ip(), args.port)
    try:
        ioloop.start()
    except KeyboardInterrupt:
        ioloop.stop()


if __name__ == "__main__":
    main()
