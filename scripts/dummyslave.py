#!/usr/bin/env python
# coding: utf-8

import time
import asyncio as aio


async def say_after(message, seconds):
    await aio.sleep(seconds)
    print(f"{message}")


async def main():
    task1 = aio.create_task(say_after("hello", 1))
    task2 = aio.create_task(say_after("world", 1))

    print(f"started at: {time.ctime()}")
    print("AA")
    await task1
    print("BB")
    await task2
    print("CC")
    print(f"finished at: {time.ctime()}")


if __name__ == '__main__':
    aio.run(main())
    
