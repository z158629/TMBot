import glob
import logging
import shutil
from sys import exit
from os import path, mkdir, getenv

logging.basicConfig(format='%(asctime)s %(levelname)s %(message)s', datefmt='%m/%d/%Y %H:%M:%S', level=logging.INFO)
logger = logging.getLogger(__name__)

BASEDIR = path.abspath(path.dirname(path.dirname(__file__)))
DATADIR =  path.join(BASEDIR, "data")
SESSIONDIR = path.join(DATADIR, "session")
TMPDIR = path.join(DATADIR, "tmp")

if not path.exists(DATADIR):
    mkdir(DATADIR)
if not path.exists(TMPDIR):
    mkdir(TMPDIR)
if not path.exists(SESSIONDIR):
    mkdir(SESSIONDIR)

SN = 0
SESSION = "TMBot"
prefix = "#"
api_id = getenv("API_ID")
api_hash = getenv("API_HASH")

if api_id is None or api_hash is None:
    exit(logger.error("缺少 API！"))

try:
    shutil.rmtree(f"{TMPDIR}/")
except Exception as e:
    pass