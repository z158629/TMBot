import re
import glob
import logging
import shutil
from sys import exit
from os import path, mkdir, getenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler

sn = 0
SESSION = "TMBot"
prefix = "#"
api_id = getenv("API_ID")
api_hash = getenv("API_HASH")
bot_token = getenv("BOT_TOKEN")

BASEDIR = path.abspath(path.dirname(path.dirname(__file__)))
DATADIR =  path.join(BASEDIR, "data")
TMPDIR = path.join(DATADIR, "tmp")
SESSIONDIR = path.join(DATADIR, "session")

class Formatter(logging.Formatter):
    def format(self, record):
        if record.levelno == logging.INFO:
            self._style._fmt = "%(asctime)s - %(levelname)s - %(name)s : %(message)s"
        else:
            color = {
                logging.WARNING: 33,
                logging.ERROR: 31,
                logging.FATAL: 31,
                logging.DEBUG: 36
            }.get(record.levelno, 0)
            self._style._fmt = f"%(asctime)s - \033[{color}m%(levelname)s\033[0m - %(name)s - (%(filename)s:%(lineno)d) : %(message)s"
        return super().format(record)

logging.getLogger("pyrogram").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)
logger = logging.getLogger(SESSION)
handler = logging.StreamHandler()
handler.setFormatter(Formatter())
logger.setLevel(logging.INFO)
logger.addHandler(handler)

if not path.exists(DATADIR):
    mkdir(DATADIR)

if not path.exists(TMPDIR):
    mkdir(TMPDIR)
else:
    shutil.rmtree(f"{TMPDIR}")
    mkdir(TMPDIR)

if not path.exists(SESSIONDIR):
    mkdir(SESSIONDIR)

if api_id is None or api_hash is None:
    exit(logger.error("缺少 API！"))

scheduler = AsyncIOScheduler()

PIPPARSER = re.compile('''^PIP\s*=\s*["']([\t a-zA-Z0-9_\-=<>!\.]+)["']\s*$''', re.M)
