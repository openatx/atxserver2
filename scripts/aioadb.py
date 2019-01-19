#!/usr/bin/env python
# coding: utf-8
#

import asyncio

async def main(loop):
    """
    Send host:version to localhost
    """
    r, w = await asyncio.open_connection("localhost", 5037, loop=loop)
    cmd = "host:version"
    print('SEND: {0}'.format(cmd))
    w.write('{:0>4x}{}'.format(len(cmd), cmd).encode())
    data = (await r.read(4)).decode()
    if data == 'OKAY':
        length = int((await r.read(4)).decode(), 16)
        message = await r.read(length)
        version_code = int(message.decode(), 16)
        print("Server Version:", version_code)
    elif data == 'FAIL':
        length = int((await r.read(4)).decode(), 16)
        message = await r.read(length)
        print("M:", message)

    print("Close the socket")
    w.close()

loop = asyncio.get_event_loop()
loop.run_until_complete(main(loop))
loop.close()
