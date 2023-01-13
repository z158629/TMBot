from .config import SESSIONDIR, SESSION, api_id, api_hash, bot_token
import uvloop
uvloop.install()
from pyrogram import Client

client = Client(SESSION, api_id=api_id, api_hash=api_hash, workdir=SESSIONDIR)

if bot_token:
    bot = Client("bot", bot_token=bot_token, api_id=api_id, api_hash=api_hash, workdir=SESSIONDIR)
else:
	bot = None