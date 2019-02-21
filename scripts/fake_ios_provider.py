#!/usr/bin/env python3
# coding: utf-8
#

import subprocess
import tornado

from logzero import logger
from tornado import gen, websocket
from tornado.ioloop import IOLoop


def exec_command(*args):
    """ exec command and get output """
    args = map(str, args)
    return subprocess.check_output(list(args))


def idevice_list():
    for line in exec_command("idevice_id", "-l").strip().split("\n"):
        if line:
            yield line


async def main():
    idevice_list()


if __name__ == '__main__':
    IOLoop.current().run_sync(main)
