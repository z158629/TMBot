from .config import SESSIONDIR, SESSION, api_id, api_hash
import uvloop
uvloop.install()
from pyrogram import Client

client = Client(SESSION, api_id=api_id, api_hash=api_hash, workdir=SESSIONDIR)
