import logging
from json import load
from string import Formatter

from fastapi import HTTPException
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from refgenconf.exceptions import RefgenconfError
from refgenconf.helpers import send_data_request
from ubiquerg import VersionInHelpParser, is_url
from yacman import get_first_env_var

from ._version import __version__ as v
from .const import *

global _LOGGER
_LOGGER = logging.getLogger(PKG_NAME)


def build_parser():
    """
    Building argument parser

    :return argparse.ArgumentParser
    """
    env_var_val = (
        get_first_env_var(CFG_ENV_VARS)[1]
        if get_first_env_var(CFG_ENV_VARS) is not None
        else "not set"
    )
    banner = "%(prog)s - refgenie web server utilities"
    additional_description = (
        "For subcommand-specific options, type: '%(prog)s <subcommand> -h'"
    )
    additional_description += "\nhttps://github.com/databio/refgenieserver"

    parser = VersionInHelpParser(
        prog=PKG_NAME, description=banner, epilog=additional_description
    )

    parser.add_argument(
        "-V", "--version", action="version", version="%(prog)s {v}".format(v=v)
    )

    msg_by_cmd = {"serve": "run the server", "archive": "prepare servable archives"}

    subparsers = parser.add_subparsers(dest="command")

    def add_subparser(cmd, description):
        return subparsers.add_parser(cmd, description=description, help=description)

    sps = {}
    # add arguments that are common for both subparsers
    for cmd, desc in msg_by_cmd.items():
        sps[cmd] = add_subparser(cmd, desc)
        sps[cmd].add_argument(
            "-c",
            "--config",
            required=False,
            dest="config",
            help=f"A path to the refgenie config file (YAML). If not provided, the "
            f"first available environment variable among: "
            f"'{', '.join(CFG_ENV_VARS)}' will be used if set. "
            f"Currently: {env_var_val}",
        ),
        sps[cmd].add_argument(
            "-d",
            "--dbg",
            action="store_true",
            dest="debug",
            help="Set logger verbosity to debug",
        )
    # add subparser-specific arguments
    sps["serve"].add_argument(
        "-p",
        "--port",
        dest="port",
        type=int,
        help="The port the webserver should be run on.",
        default=DEFAULT_PORT,
    )
    sps["archive"].add_argument(
        "--genomes-desc",
        dest="genomes_desc",
        type=str,
        default=None,
        help="Path to a CSV file with genomes descriptions. "
        "Format: genome_name, genome description",
    )
    sps["archive"].add_argument(
        "-f",
        "--force",
        action="store_true",
        dest="force",
        help="whether the server file tree should be rebuilt even if exists",
    )
    sps["archive"].add_argument(
        "-r",
        "--remove",
        action="store_true",
        dest="remove",
        help="Remove selected genome, genome/asset or genome/asset:tag",
    )
    sps["archive"].add_argument(
        "asset_registry_paths",
        metavar="asset-registry-paths",
        type=str,
        nargs="*",
        help="One or more registry path strings that identify assets, e.g. hg38/fasta:tag",
    )
    return parser


def preprocess_attrs(attrs):
    """
    Based on the CHANGED_KEYS mapping (new_key:old_key), rename the keys in the provided one

    :param yacman.YacAttMap attrs: mapping to process
    :return yacman.YacAttMap: mapping with renamed key names
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
        _LOGGER.debug(f"Could not determine openAPI version: {str(e)}")
        return "3.0.2"


def get_datapath_for_genome(
    rgc, fill_dict, pth_templ="{base}/{genome}/{file_name}", remote_key=None
):
    """
    Get the path to the data file to serve.

    Depending on the remote URL base being set or not, the function will return
    either a remote URL to the file or a file path along with a flag indicating
    the source

    :param refgenconf.RefGenConf rgc: configuration object to use
    :param dict fill_dict: a dictionary to use to fill in the path template
    :param str pth_templ: the path template
    :return (str, bool): a pair of file source and the flag indicating whether
        the source is remote
    """
    req_keys = [i[1] for i in Formatter().parse(pth_templ) if i[1] is not None]
    assert all(
        [k in req_keys for k in list(fill_dict.keys())]
    ), f"Only the these keys are allowed in the fill_dict: {req_keys}"
    fill_dict.update({"base": BASE_DIR})
    # fill_dict.update({"base": rgc["genome_archive_folder"]})
    remote = is_data_remote(rgc)
    if remote:
        if remote_key is None:
            raise ValueError(
                f"'remotes' key found in config; the 'remote_key' argument must "
                f"be one of: {list(rgc['remotes'].keys())} "
            )
        if remote_key not in rgc["remotes"]:
            raise KeyError(
                f"In remotes mapping the '{remote_key}' not found. "
                f"Can't determine a data path prefix identified by this key."
            )
        # at this point we know that the 'remotes' mapping has the 'remote_key' key
        # and the value is a dict with 'prefix' key defined.
        fill_dict["base"] = rgc["remotes"][remote_key]["prefix"].rstrip("/")
    return pth_templ.format(**fill_dict), remote


def is_data_remote(rgc):
    """
    Determine if server genome config defines a 'remotes' key, 'http is one of them and
     additionally assert the correct structure -- 'prefix' key defined.

    :param refgenconf.RefGenConf rgc: server genome config object
    :return bool: whether remote data source is configured
    """
    return (
        True
        if "remotes" in rgc
        and isinstance(rgc["remotes"], dict)
        and all(
            [
                "prefix" in r and isinstance(r["prefix"], str)
                for r in rgc["remotes"].values()
            ]
        )
        else False
    )


def purge_nonservable(rgc):
    """
    Remove entries in RefGenConf object that were not processed by the archiver
    and should not be served

    :param refgenconf.RefGenConf rgc: object to check
    :return refgenconf.RefGenConf: object with just the servable entries
    """

    def _check_servable(rgc, genome, asset, tag):
        tag_data = rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset][
            CFG_ASSET_TAGS_KEY
        ][tag]
        return all(
            [r in tag_data for r in [CFG_ARCHIVE_CHECKSUM_KEY, CFG_ARCHIVE_SIZE_KEY]]
        )

    for genome_name, genome in rgc[CFG_GENOMES_KEY].items():
        for asset_name, asset in genome[CFG_ASSETS_KEY].items():
            try:
                for tag_name, tag in asset[CFG_ASSET_TAGS_KEY].items():
                    if not _check_servable(rgc, genome_name, asset_name, tag_name):
                        _LOGGER.debug(
                            "Removing '{}/{}:{}', it's not servable".format(
                                genome_name, asset_name, tag_name
                            )
                        )
                        rgc.cfg_remove_assets(genome_name, asset_name, tag_name)
            except KeyError:
                rgc.cfg_remove_assets(genome_name, asset_name)
    return rgc


def safely_get_example(rgc, entity, rgc_method, default, **kwargs):
    try:
        res = rgc.__getattr__(rgc_method)(**kwargs)
        return res[0] if isinstance(res, list) else res
    except Exception as e:
        _LOGGER.warning(
            f"Caught exception: {e}\n"
            f"Failed to create {entity} example! Using '{default}', which might not exist"
        )
        return default


def create_asset_file_path(rgc, genome, asset, tag, seek_key, remote_key="http"):
    """
    Construct a path to an unarchived asset file

    :param str genome:
    :param str asset:
    :param str tag:
    """
    tag = tag or rgc.get_default_tag(
        genome, asset
    )  # returns 'default' for nonexistent genome/asset; no need to catch
    try:
        rgc._assert_gat_exists(gname=genome, aname=asset, tname=tag)
    except RefgenconfError:
        msg = MSG_404.format(f"asset ({genome}/{asset}:{tag})")
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)
    tag_dict = rgc.genomes[genome][CFG_ASSETS_KEY][asset][CFG_ASSET_TAGS_KEY][tag]
    if seek_key not in tag_dict[CFG_SEEK_KEYS_KEY]:
        msg = MSG_404.format(f"seek_key ({genome}/{asset}.{seek_key}:{tag})")
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)
    seek_key_target = tag_dict[CFG_SEEK_KEYS_KEY][seek_key]
    # append the seek_key value to the path only if it isn't the "dir" seek_key.
    # Otherwise the result would be a path ending with "\."
    file_name = (
        f"{asset}__{tag}/{seek_key_target}" if seek_key != "dir" else f"{asset}__{tag}/"
    )
    path, _ = get_datapath_for_genome(
        rgc, dict(genome=genome, file_name=file_name), remote_key=remote_key
    )
    _LOGGER.info(f"serving asset file path: {path}")
    return path


def serve_file_for_asset(rgc, genome, asset, tag, template):
    """
    Serve a file, like log file

    :param str genome: genome name
    :param str asset: asset name
    :param str tag: tag name
    :param ste template: file name template with place for asset and tag names,
        e.g. 'build_log_{}__{}.md'
    """
    # returns 'default' for nonexistent genome/asset; no need to catch
    tag = tag or rgc.get_default_tag(genome, asset)
    file_name = template.format(asset, tag)
    path, remote = get_datapath_for_genome(
        rgc, dict(genome=genome, file_name=file_name), remote_key="http"
    )
    if remote:
        _LOGGER.info(f"redirecting to URL: '{path}'")
        return RedirectResponse(path)
    _LOGGER.info(f"serving file: '{path}'")
    if os.path.isfile(path):
        return FileResponse(
            path, filename=file_name, media_type="application/octet-stream"
        )
    else:
        msg = MSG_404.format(f"asset ({genome}/{asset}:{tag})")
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)


def serve_json_for_asset(rgc, genome, asset, tag, template):
    """
    Serve a JSON object, like recipe or asset dir contents for an asset

    :param str genome: genome name
    :param str asset: asset name
    :param str tag: tag name
    :param ste template: file name template with place for asset and tag names,
        e.g. 'build_recipe_{}__{}.json'
    """
    # returns 'default' for nonexistent genome/asset; no need to catch
    tag = tag or rgc.get_default_tag(genome, asset)
    file_name = template.format(asset, tag)
    path, remote = get_datapath_for_genome(
        rgc, dict(genome=genome, file_name=file_name), remote_key="http"
    )
    if remote:
        _LOGGER.info(f"redirecting to URL: '{path}'")
        return RedirectResponse(path)
    _LOGGER.info(f"serving JSON: '{path}'")
    if os.path.isfile(path):
        with open(path, "r") as f:
            recipe = load(f)
        return JSONResponse(recipe)
    else:
        msg = MSG_404.format(f"asset ({asset})")
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)


def get_asset_dir_contents(rgc, genome, asset, tag):
    """
    Get the asset directory contents into a list

    :param refgenconf.RefGenConf rgc: config
    :param str genome: genome name
    :param str asset: asset name
    :param str tag: tag name
    :return list[str]: list of files in the asset directory
    """
    # returns 'default' for nonexistent genome/asset; no need to catch
    tag = tag or rgc.get_default_tag(genome, asset)
    file_name = TEMPLATE_ASSET_DIR_CONTENTS.format(asset, tag)
    path, remote = get_datapath_for_genome(
        rgc, dict(genome=genome, file_name=file_name), remote_key="http"
    )
    if is_url(path):
        _LOGGER.debug(f"Asset dir contents path is a URL: {path}")
        dir_contents = send_data_request(url=path)
    elif os.path.exists(path):
        _LOGGER.debug(f"Asset dir contents path is a file: {path}")
        with open(path) as f:
            dir_contents = load(f)
    else:
        raise TypeError(f"Path is neither a valid URL nor an existing file: {path}")
    _LOGGER.debug(f"Asset dir contents: {dir_contents}")
    return dir_contents
