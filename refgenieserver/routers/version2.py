from copy import copy

from fastapi import APIRouter, HTTPException
from refgenconf.helpers import replace_str_in_obj
from refgenconf.refgenconf import map_paths_by_id
from starlette.requests import Request
from starlette.responses import FileResponse, JSONResponse, RedirectResponse
from ubiquerg import parse_registry_path

from ..const import *
from ..helpers import get_datapath, get_openapi_version
from ..main import _LOGGER, app, rgc, templates

router = APIRouter()

api_version_tags = [API2_ID]


@router.get("/", tags=api_version_tags)
@router.get("/index", tags=api_version_tags)
async def index(request: Request):
    """
    Returns a landing page HTML with the server resources ready do download. No inputs required.
    """
    _LOGGER.debug("RefGenConf object:\n{}".format(rgc))
    templ_vars = {
        "request": request,
        "genomes": rgc[CFG_GENOMES_KEY],
        "rgc": rgc[CFG_GENOMES_KEY],
        "openapi_version": get_openapi_version(app),
    }
    _LOGGER.debug("merged vars: {}".format(dict(templ_vars, **ALL_VERSIONS)))
    return templates.TemplateResponse("index.html", dict(templ_vars, **ALL_VERSIONS))


@router.get("/asset/{genome}/{asset}/splash", tags=api_version_tags)
async def asset_splash_page(request: Request, genome: str, asset: str, tag: str = None):
    """
    Returns an asset splash page
    """
    tag = tag or rgc.get_default_tag(
        genome, asset
    )  # returns 'default' for nonexistent genome/asset; no need to catch
    links_dict = {
        OPERATION_IDS["asset"][oid]: path.format(genome=genome, asset=asset, tag=tag)
        for oid, path in map_paths_by_id(app.openapi()).items()
        if oid in OPERATION_IDS["asset"].keys()
    }
    templ_vars = {
        "request": request,
        "genome": genome,
        "asset": asset,
        "tag": tag,
        "rgc": rgc,
        "prp": parse_registry_path,
        "links_dict": links_dict,
        "openapi_version": get_openapi_version(app),
    }
    _LOGGER.debug("merged vars: {}".format(dict(templ_vars, **ALL_VERSIONS)))
    return templates.TemplateResponse("asset.html", dict(templ_vars, **ALL_VERSIONS))


@router.get("/genomes", tags=api_version_tags)
async def list_available_genomes():
    """
    Returns a list of genomes this server holds at least one asset for. No inputs required.
    """
    _LOGGER.info("serving genomes string: '{}'".format(rgc.genomes_str()))
    return rgc.genomes_list()


@router.get("/assets", operation_id=API_ID_ASSETS, tags=api_version_tags)
async def list_available_assets():
    """
    Returns a list of all assets that can be downloaded. No inputs required.
    """
    ret_dict = rgc.list(include_tags=True)
    _LOGGER.info("serving assets dict: {}".format(ret_dict))
    return ret_dict


@router.get(
    "/asset/{genome}/{asset}/archive",
    operation_id=API_ID_ARCHIVE,
    tags=api_version_tags,
)
async def download_asset(genome: str, asset: str, tag: str = None):
    """
    Returns an archive. Requires the genome name and the asset name as an input.

    Optionally, 'tag' query parameter can be specified to get a tagged asset archive. Default tag is returned otherwise.
    """
    tag = tag or rgc.get_default_tag(
        genome, asset
    )  # returns 'default' for nonexistent genome/asset; no need to catch
    file_name = "{}__{}{}".format(asset, tag, ".tgz")
    path, remote = get_datapath(
        rgc,
        dict(
            genome=rgc.get_genome_alias(digest=genome, fallback=True),
            file_name=file_name,
        ),
        remote_key="http",
    )
    _LOGGER.info("file source: {}".format(path))
    if remote:
        _LOGGER.info("redirecting to URL: '{}'".format(path))
        return RedirectResponse(path)
    _LOGGER.info("serving asset file: '{}'".format(path))
    if os.path.isfile(path):
        return FileResponse(
            path, filename=file_name, media_type="application/octet-stream"
        )
    else:
        msg = MSG_404.format("asset ({})".format(asset))
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)


@router.get(
    "/asset/{genome}/{asset}/default_tag",
    operation_id=API_ID_DEFAULT_TAG,
    tags=api_version_tags,
)
async def get_asset_default_tag(genome: str, asset: str):
    """
    Returns the default tag name. Requires genome name and asset name as an input.
    """
    return rgc.get_default_tag(genome, asset)


@router.get(
    "/asset/{genome}/{asset}/{tag}/asset_digest",
    operation_id=API_ID_DIGEST,
    tags=api_version_tags,
)
async def get_asset_digest(genome: str, asset: str, tag: str):
    """
    Returns the asset digest. Requires genome name asset name and tag name as an input.
    """
    try:
        return rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset][CFG_ASSET_TAGS_KEY][
            tag
        ][CFG_ASSET_CHECKSUM_KEY]
    except KeyError:
        msg = MSG_404.format(
            "genome/asset:tag combination ({}/{}:{})".format(genome, asset, tag)
        )
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)


@router.get(
    "/asset/{genome}/{asset}/{tag}/archive_digest",
    operation_id=API_ID_ARCHIVE_DIGEST,
    tags=api_version_tags,
)
async def get_archive_digest(genome: str, asset: str, tag: str):
    """
    Returns the archive digest. Requires genome name asset name and tag name as an input.
    """
    try:
        return rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset][CFG_ASSET_TAGS_KEY][
            tag
        ][CFG_ARCHIVE_CHECKSUM_KEY]
    except KeyError:
        msg = MSG_404.format(
            "genome/asset:tag combination ({}/{}:{})".format(genome, asset, tag)
        )
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)


@router.get(
    "/asset/{genome}/{asset}/log", operation_id=API_ID_LOG, tags=api_version_tags
)
async def download_asset_build_log(genome: str, asset: str, tag: str = None):
    """
    Returns a build log. Requires the genome name and the asset name as an input.

    Optionally, 'tag' query parameter can be specified to get a tagged asset archive. Default tag is returned otherwise.
    """
    tag = tag or rgc.get_default_tag(
        genome, asset
    )  # returns 'default' for nonexistent genome/asset; no need to catch
    file_name = TEMPLATE_LOG.format(asset, tag)
    path, remote = get_datapath(
        rgc,
        dict(
            genome=rgc.get_genome_alias(digest=genome, fallback=True),
            file_name=file_name,
        ),
        remote_key="http",
    )
    if remote:
        _LOGGER.info("redirecting to URL: '{}'".format(path))
        return RedirectResponse(path)
    _LOGGER.info("serving build log file: '{}'".format(path))
    if os.path.isfile(path):
        return FileResponse(
            path, filename=file_name, media_type="application/octet-stream"
        )
    else:
        msg = MSG_404.format("asset ({})".format(asset))
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)


@router.get(
    "/asset/{genome}/{asset}/recipe", operation_id=API_ID_RECIPE, tags=api_version_tags
)
async def download_asset_build_recipe(genome: str, asset: str, tag: str = None):
    """
    Returns a build recipe. Requires the genome name and the asset name as an input.

    Optionally, 'tag' query parameter can be specified to get a tagged asset archive. Default tag is returned otherwise.
    """
    tag = tag or rgc.get_default_tag(
        genome, asset
    )  # returns 'default' for nonexistent genome/asset; no need to catch
    file_name = TEMPLATE_RECIPE_JSON.format(asset, tag)
    path, remote = get_datapath(
        rgc,
        dict(
            genome=rgc.get_genome_alias(digest=genome, fallback=True),
            file_name=file_name,
        ),
        remote_key="http",
    )
    if remote:
        _LOGGER.info("redirecting to URL: '{}'".format(path))
        return RedirectResponse(path)
    _LOGGER.info("serving build log file: '{}'".format(path))
    if os.path.isfile(path):
        import json

        with open(path, "r") as f:
            recipe = json.load(f)
        return JSONResponse(recipe)
    else:
        msg = MSG_404.format("asset ({})".format(asset))
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)


@router.get(
    "/asset/{genome}/{asset}", operation_id=API_ID_ASSET_ATTRS, tags=api_version_tags
)
async def download_asset_attributes(genome: str, asset: str, tag: str = None):
    """
    Returns a dictionary of asset attributes, like archive size, archive digest etc.
    Requires the genome name and the asset name as an input.
    Optionally, 'tag' query parameter can be specified to get a tagged asset attributes.
    """
    tag = tag or rgc.get_default_tag(
        genome, asset
    )  # returns 'default' for nonexistent genome/asset; no need to catch
    try:
        attrs = rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset][CFG_ASSET_TAGS_KEY][
            tag
        ]
        attrs_copy = copy(attrs)
        if CFG_LEGACY_ARCHIVE_CHECKSUM_KEY in attrs_copy:
            # TODO: remove in future releases
            # new asset archives consist of different file names, so the new
            # archive digest does not match the old archives. Therefore the
            # archiver saves the old archive digest along with the new. So in
            # this API version we need to swap them and remove the old afterwards
            attrs_copy[CFG_ARCHIVE_CHECKSUM_KEY] = attrs_copy[
                CFG_LEGACY_ARCHIVE_CHECKSUM_KEY
            ]
            del attrs_copy[CFG_LEGACY_ARCHIVE_CHECKSUM_KEY]
        _LOGGER.info(f"attributes returned for {genome}/{asset}:{tag}: \n{attrs_copy}")
        return replace_str_in_obj(
            attrs_copy,
            x=rgc.get_genome_alias_digest(alias=genome, fallback=True),
            y=rgc.get_genome_alias(digest=genome, fallback=True),
        )
    except KeyError:
        msg = MSG_404.format(
            "genome/asset:tag combination ({}/{}:{})".format(genome, asset, tag)
        )
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)


@router.get("/genome/{genome}/genome_digest", tags=api_version_tags)
async def download_genome_digest(genome: str):
    """
    Returns the genome digest. Requires the genome name as an input
    """
    try:
        digest = rgc.get_genome_alias_digest(alias=genome)
        _LOGGER.info("digest returned for '{}': {}".format(genome, digest))
        return digest
    except KeyError:
        msg = MSG_404.format("genome ({})".format(genome))
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)


@router.get("/genome/{genome}", operation_id=API_ID_GENOME_ATTRS, tags=api_version_tags)
async def download_genome_attributes(genome: str):
    """
    Returns a dictionary of genome attributes, like archive size, archive digest etc.
    Requires the genome name name as an input.
    """
    try:
        attrs = rgc.get_genome_attributes(genome)
        _LOGGER.info(
            "attributes returned for genome '{}': \n{}".format(genome, str(attrs))
        )
        return attrs
    except KeyError:
        msg = MSG_404.format("genome ({})".format(genome))
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)


@router.get("/genomes/{asset}", tags=api_version_tags)
async def list_genomes_by_asset(asset: str):
    """
    Returns a list of genomes that have the requested asset defined. Requires the asset name as an input.
    """
    genomes = rgc.list_genomes_by_asset(asset)
    _LOGGER.info("serving genomes by '{}' asset: {}".format(asset, genomes))
    return genomes
