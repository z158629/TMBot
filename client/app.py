import uvloop
uvloop.install()
from pyrogram import Client
from .config import SESSIONDIR, SESSION, api_id, api_hash

client = Client(SESSION, api_id=api_id, api_hash=api_hash, workdir=SESSIONDIR)
