from __future__ import annotations

import argparse
import logging
from json import load
from string import Formatter
from typing import TYPE_CHECKING, Any

from fastapi import HTTPException
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from refgenconf.exceptions import RefgenconfError
from refgenconf.helpers import send_data_request
from ubiquerg import VersionInHelpParser, is_url
from yacman import get_first_env_var

if TYPE_CHECKING:
    from fastapi import FastAPI
    from refgenconf import RefGenConf
    from starlette.responses import Response

from ._version import __version__ as v
from .const import *

global _LOGGER
_LOGGER = logging.getLogger(PKG_NAME)


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser.

    Returns:
        The configured argument parser.
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
        (
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
        )
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


def preprocess_attrs(attrs: dict) -> dict:
    """Rename keys based on the CHANGED_KEYS mapping (new_key:old_key).

    Args:
        attrs: Mapping to process.

    Returns:
        Mapping with renamed key names.
    """
    from copy import deepcopy

    attrs_cpy = deepcopy(attrs)
    for new_key in CHANGED_KEYS.keys():
        if new_key in attrs_cpy:
            attrs_cpy[CHANGED_KEYS[new_key]] = attrs_cpy[new_key]
            del attrs_cpy[new_key]
    return attrs_cpy


def get_openapi_version(app: FastAPI) -> str:
    """Get the OpenAPI version from the OpenAPI description JSON.

    Args:
        app: FastAPI app object.

    Returns:
        The openAPI version in use.
    """
    try:
        return app.openapi()["openapi"]
    except Exception as e:
        _LOGGER.debug(f"Could not determine openAPI version: {str(e)}")
        return "3.0.2"


def get_datapath_for_genome(
    rgc: RefGenConf,
    fill_dict: dict[str, str],
    pth_templ: str = "{base}/{genome}/{file_name}",
    remote_key: str | None = None,
) -> tuple[str, bool]:
    """Get the path to the data file to serve.

    Depending on the remote URL base being set or not, returns either a remote
    URL to the file or a file path along with a flag indicating the source.

    Args:
        rgc: Configuration object to use.
        fill_dict: Dictionary to fill in the path template.
        pth_templ: The path template.
        remote_key: Key identifying the remote data provider.

    Returns:
        A pair of (file source, is_remote flag).
    """
    req_keys = [i[1] for i in Formatter().parse(pth_templ) if i[1] is not None]
    assert all([k in req_keys for k in list(fill_dict.keys())]), (
        f"Only the these keys are allowed in the fill_dict: {req_keys}"
    )
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


def is_data_remote(rgc: RefGenConf) -> bool:
    """Determine if the server genome config defines a remote data source.

    Checks for a 'remotes' key with correct structure (each remote has a
    'prefix' key defined).

    Args:
        rgc: Server genome config object.

    Returns:
        Whether a remote data source is configured.
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


def purge_nonservable(rgc: RefGenConf) -> RefGenConf:
    """Remove entries not processed by the archiver that should not be served.

    Args:
        rgc: Configuration object to check.

    Returns:
        The configuration object with only servable entries.
    """

    def _check_servable(rgc: RefGenConf, genome: str, asset: str, tag: str) -> bool:
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


def safely_get_example(
    rgc: RefGenConf, entity: str, rgc_method: str, default: str, **kwargs: Any
) -> str:
    """Safely get an example value from the config, falling back to a default.

    Args:
        rgc: Configuration object.
        entity: Description of the entity for logging.
        rgc_method: Name of the method to call on rgc.
        default: Fallback value if the method call fails.
        **kwargs: Additional keyword arguments passed to the method.

    Returns:
        The first result element (if list) or the result itself, or the default.
    """
    try:
        res = rgc.__getattr__(rgc_method)(**kwargs)
        return res[0] if isinstance(res, list) else res
    except Exception as e:
        _LOGGER.warning(
            f"Caught exception: {e}\n"
            f"Failed to create {entity} example! Using '{default}', which might not exist"
        )
        return default


def create_asset_file_path(
    rgc: RefGenConf,
    genome: str,
    asset: str,
    tag: str | None,
    seek_key: str,
    remote_key: str = "http",
) -> str:
    """Construct a path to an unarchived asset file.

    Args:
        rgc: Configuration object.
        genome: Genome name.
        asset: Asset name.
        tag: Tag name.
        seek_key: Seek key name.
        remote_key: Remote data provider key.

    Returns:
        Path to the asset file.

    Raises:
        HTTPException: If the asset or seek key is not found.
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


def serve_file_for_asset(
    rgc: RefGenConf, genome: str, asset: str, tag: str | None, template: str
) -> Response:
    """Serve a file, like a build log.

    Args:
        rgc: Configuration object.
        genome: Genome name.
        asset: Asset name.
        tag: Tag name.
        template: File name template with placeholders for asset and tag names,
            e.g. 'build_log_{}__{}.md'.

    Returns:
        A RedirectResponse for remote files, or a FileResponse for local files.

    Raises:
        HTTPException: If the file is not found.
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


def serve_json_for_asset(
    rgc: RefGenConf, genome: str, asset: str, tag: str | None, template: str
) -> Response:
    """Serve a JSON object, like a recipe or asset directory contents.

    Args:
        rgc: Configuration object.
        genome: Genome name.
        asset: Asset name.
        tag: Tag name.
        template: File name template with placeholders for asset and tag names,
            e.g. 'build_recipe_{}__{}.json'.

    Returns:
        A RedirectResponse for remote files, or a JSONResponse for local files.

    Raises:
        HTTPException: If the file is not found.
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


def get_asset_dir_contents(
    rgc: RefGenConf, genome: str, asset: str, tag: str | None
) -> list:
    """Get the asset directory contents as a list.

    Args:
        rgc: Configuration object.
        genome: Genome name.
        asset: Asset name.
        tag: Tag name.

    Returns:
        List of files in the asset directory.

    Raises:
        TypeError: If the path is neither a valid URL nor an existing file.
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
