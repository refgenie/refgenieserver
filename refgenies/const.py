""" Package constants """
import os

DEFAULT_PORT = 80
BASE_FOLDER = "/genomes"
BASE_URL = "http://big.databio.org/refgenie_files"
CFG_GENOMES_KEY = "genomes"
CFG_ARCHIVE_KEY = "genome_archive"
CFG_FOLDER_KEY = "genome_folder"
CFG_ARCHIVE_SIZE_KEY = "archive_size"
CFG_ASSET_SIZE_KEY = "asset_size"
CFG_CHECKSUM_KEY = "archive_checksum"
CFG_PATH_KEY = "path"
TEMPLATES_DIRNAME = "templates"
TEMPLATES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), TEMPLATES_DIRNAME)
STATIC_DIRNAME = "static"
STATIC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), STATIC_DIRNAME)
TGZ = dict(ext=".tgz", flags="-cvzf")
TAR = dict(ext=".tar", flags="-cvf")

CFG_KEYS = ["CFG_ARCHIVE_KEY", "CFG_FOLDER_KEY", "CFG_GENOMES_KEY", "CFG_ARCHIVE_SIZE_KEY",
            "CFG_CHECKSUM_KEY", "CFG_ASSET_SIZE_KEY", "CFG_PATH_KEY"]
