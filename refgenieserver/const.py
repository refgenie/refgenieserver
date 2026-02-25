"""Package constants"""

from __future__ import annotations

import os
from platform import python_version

from refgenconf._version import __version__ as rgc_v
from refgenconf.const import *

from ._version import __version__ as server_v

ALL_VERSIONS: dict[str, str] = {
    "server_version": server_v,
    "rgc_version": rgc_v,
    "python_version": python_version(),
}
PKG_NAME: str = "refgenieserver"
DEFAULT_PORT: int = 80
BASE_DIR: str = "/genomes"
# if running outside of the Docker container 'BASE_DIR' can be replaced with rgc[CFG_ARCHIVE_KEY]
TEMPLATES_DIRNAME: str = "templates"
TEMPLATES_PATH: str = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), TEMPLATES_DIRNAME
)
STATIC_DIRNAME: str = "static"
STATIC_PATH: str = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), STATIC_DIRNAME
)
LOG_FORMAT: str = "%(levelname)s in %(funcName)s: %(message)s"
MSG_404: str = "No such {} on server"
DESC_PLACEHOLDER: str = "No description"
CHECKSUM_PLACEHOLDER: str = "No digest"
# Here we define the key name changes; format: {"new_key": "old_key"}
# This dict is then used to pre-process the attributes dict before serving to the old versions of the client
CHANGED_KEYS: dict[str, str] = {CFG_ASSET_PATH_KEY: "path"}

# TODO: to be removed in the future
CFG_LEGACY_ARCHIVE_CHECKSUM_KEY: str = "legacy_archive_digest"

API1_ID: str = "APIv1"
API2_ID: str = "APIv2"
API3_ID: str = "APIv3"
PRIV_API_ID: str = "PRIVATE_API"


TAGS_METADATA: list[dict[str, str]] = [
    {
        "name": API3_ID,
        "description": "These are the most recent API endpoints. "
        "They are prepended with `v3` or nothing. ",
    },
    {
        "name": API2_ID,
        "description": "These are deprecated endpoints that may be removed in the future. "
        "They are prepended with `v2`.",
    },
    {
        "name": API1_ID,
        "description": "These are deprecated endpoints that may be removed in the future. "
        "They are prepended with `v1`.",
    },
    {
        "name": PRIV_API_ID,
        "description": "These are private endpoints that may change anytime. "
        "They are prepended with `_private_api`.",
    },
]
