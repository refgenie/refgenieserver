""" Package constants """
import os

DEFAULT_PORT = 80
BASE_FOLDER = "/genomes"
BASE_URL = "http://big.databio.org/refgenie_files"
CFG_GENOMES_KEY = "genomes"
TEMPLATES_DIRNAME = "templates"
TEMPLATES_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), TEMPLATES_DIRNAME)
STATIC_DIRNAME = "static"
STATIC_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), STATIC_DIRNAME)