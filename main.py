#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 现学现卖、东拼西凑的玩意

import asyncio
from pyrogram import idle
from client.app import client
from client.config import logger
from client.utils import loadPlugins, scheduler

async def main():
    logger.info('Started')
    asyncio.ensure_future(loadPlugins())
    scheduler.start()
    await client.start()
    await idle()
    await client.stop()

if __name__ == '__main__':
    client.run(main())
