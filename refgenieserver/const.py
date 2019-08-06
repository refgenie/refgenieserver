""" Package constants """
import os
from refgenconf.const import *
from refgenconf._version import __version__ as rgc_v
from ._version import __version__ as server_v
from platform import python_version
ALL_VERSIONS = {"server_version": server_v, "rgc_version": rgc_v, "python_version": python_version()}
PKG_NAME = "refgenieserver"
DEFAULT_PORT = 80
BASE_DIR = "/genomes"
# if running outside of the Docker container 'BASE_DIR' can be replaced with rgc[CFG_ARCHIVE_KEY] in 'main.py'
TEMPLATES_DIRNAME = "templates"
TEMPLATES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), TEMPLATES_DIRNAME)
STATIC_DIRNAME = "static"
STATIC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), STATIC_DIRNAME)
TGZ = dict(ext=".tgz", flags="-cvzf")
TAR = dict(ext=".tar", flags="-cvf")
FILE_SIZE_UNITS = ['B', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB']
LOG_FORMAT = "%(levelname)s in %(funcName)s: %(message)s"
MSG_404 = "No such {} on server"
DESC_PLACEHOLDER = "No description"
CHECKSUM_PLACEHOLDER = "No checksum"
CONTENTS_PLACEHOLDER = "No contents"
