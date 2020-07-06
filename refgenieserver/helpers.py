import logging
from .const import *
from ._version import __version__ as v
from yacman import get_first_env_var
from ubiquerg import VersionInHelpParser

from string import Formatter

global _LOGGER
_LOGGER = logging.getLogger(PKG_NAME)


def build_parser():
    """
    Building argument parser

    :return argparse.ArgumentParser
    """
    env_var_val = get_first_env_var(CFG_ENV_VARS)[1] if get_first_env_var(CFG_ENV_VARS) is not None else "not set"
    banner = "%(prog)s - refgenie web server utilities"
    additional_description = "For subcommand-specific options, type: '%(prog)s <subcommand> -h'"
    additional_description += "\nhttps://github.com/databio/refgenieserver"

    parser = VersionInHelpParser(
        prog=PKG_NAME,
        description=banner,
        epilog=additional_description)

    parser.add_argument(
        "-V", "--version",
        action="version",
        version="%(prog)s {v}".format(v=v))

    msg_by_cmd = {
        "serve": "run the server",
        "archive": "prepare servable archives"}

    subparsers = parser.add_subparsers(dest="command")

    def add_subparser(cmd, description):
        return subparsers.add_parser(
            cmd, description=description, help=description)

    sps = {}
    # add arguments that are common for both subparsers
    for cmd, desc in msg_by_cmd.items():
        sps[cmd] = add_subparser(cmd, desc)
        sps[cmd].add_argument(
            '-c', '--config', required=False, dest="config",
            help="A path to the refgenie config file (YAML). If not provided, the first available environment variable "
                 "among: \'{}\' will be used if set. Currently: {}".format(", ".join(CFG_ENV_VARS), env_var_val))
        sps[cmd].add_argument(
            "-d", "--dbg",
            action="store_true",
            dest="debug",
            help="Set logger verbosity to debug")
    # add subparser-specific arguments
    sps["serve"].add_argument(
        "-p", "--port",
        dest="port",
        type=int,
        help="The port the webserver should be run on.", default=DEFAULT_PORT)
    sps["archive"].add_argument(
        "--genomes-desc",
        dest="genomes_desc",
        type=str,
        default=None,
        help="Path to a CSV file with genomes descriptions. Format: genome_name, genome description")
    sps["archive"].add_argument(
        "-f", "--force",
        action="store_true",
        dest="force",
        help="whether the server file tree should be rebuilt even if exists")
    sps["archive"].add_argument(
        "-r", "--remove",
        action="store_true",
        dest="remove",
        help="Remove selected genome, genome/asset or genome/asset:tag")
    sps["archive"].add_argument(
        "asset_registry_paths", metavar="asset-registry-paths", type=str, nargs='*',
        help="One or more registry path strings that identify assets, e.g. hg38/fasta:tag")
    return parser


def preprocess_attrs(attrs):
    """
    Based on the CHANGED_KEYS mapping (new_key:old_key), rename the keys in the provided one

    :param yacman.yacman.YacAttMap attrs: mapping to process
    :return yacman.yacman.YacAttMap: mapping with renamed key names
    """
    from copy import deepcopy
    attrs_cpy = deepcopy(attrs)
    for new_key in CHANGED_KEYS.keys():
        if new_key in attrs_cpy:
            attrs_cpy[CHANGED_KEYS[new_key]] = attrs_cpy[new_key]
            del attrs_cpy[new_key]
    return attrs_cpy


def get_openapi_version(app):
    """
    Get the OpenAPI version from the OpenAPI description JSON

    :param fastapi.FastAPI app: app object
    :return str: openAPI version in use
    """
    try:
        return app.openapi()["openapi"]
    except Exception as e:
        return "3.0.2"


def get_datapath_for_genome(rgc, fill_dict,
                            pth_templ="{base}/{genome}/{file_name}"):
    """
    Get the path to the data file to serve.

    Depending on the remote URL base being set or not, the function will return
    either a remote URL to the file or a file path along with a flag indicating
    the source

    :param refgenconf.RefGenConf rgc: configiration object to use
    :param dict fill_dict: a dictionary to use to fill in the path template
    :param str fill_dict: the path template
    :return (str, bool): a pair of file source and the flag indicationg whether
     the source is remote
    """
    req_keys = [i[1] for i in Formatter().parse(pth_templ) if i[1] is not None]
    assert all([k in req_keys for k in list(fill_dict.keys())]), \
        "Only the following keys are allowed in the fill_dict: {}".format(req_keys)
    remote = False
    fill_dict.update({"base": BASE_DIR})
    if CFG_REMOTE_URL_BASE_KEY in rgc \
            and rgc[CFG_REMOTE_URL_BASE_KEY] is not None:
        fill_dict["base"] = rgc[CFG_REMOTE_URL_BASE_KEY].rstrip("/")
        remote = True
    return pth_templ.format(**fill_dict), remote


def purge_nonservable(rgc):
    """
    Remove entries in RefGenConf object that were not processed by the archiver and should not be served

    :param refgenconf.RefGenConf rgc: object to check
    :return refgenconf.RefGenConf: object with just the servable entries
    """
    def _check_servable(rgc, genome, asset, tag):
        tag_data = rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset][CFG_ASSET_TAGS_KEY][tag]
        return all([r in tag_data for r in [CFG_ARCHIVE_CHECKSUM_KEY, CFG_ARCHIVE_SIZE_KEY]])

    for genome_name, genome in rgc[CFG_GENOMES_KEY].items():
        for asset_name, asset in genome[CFG_ASSETS_KEY].items():
            try:
                for tag_name, tag in asset[CFG_ASSET_TAGS_KEY].items():
                    if not _check_servable(rgc, genome_name, asset_name, tag_name):
                        _LOGGER.debug("Removing '{}/{}:{}', it's not servable".format(genome_name, asset_name, tag_name))
                        rgc.cfg_remove_assets(genome_name, asset_name, tag_name)
            except KeyError:
                rgc.cfg_remove_assets(genome_name, asset_name)
    return rgc
