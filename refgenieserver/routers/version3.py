from starlette.responses import FileResponse, JSONResponse, RedirectResponse
from starlette.requests import Request
from fastapi import HTTPException, APIRouter, Path, Query
from typing import Optional


from ubiquerg import parse_registry_path
from refgenconf.refgenconf import map_paths_by_id
from yacman import UndefinedAliasError

from ..const import *
from ..main import rgc, templates, _LOGGER, app
from ..helpers import get_openapi_version, get_datapath_for_genome

router = APIRouter()

# API query path definitions
g = Path(..., description="Genome digest", regex=r"^\w+$", max_length=48, min_length=48)
a = Path(..., description="Asset name", regex=r"^\S+$")
t = Path(..., description="Tag name", regex=r"^\S+$")
# API query parameter definitions
tq = Query(None, description="Tag name", regex=r"^\S+$")


@router.get("/")
@router.get("/index")
async def index(request: Request):
    """
    Returns a landing page HTML with the server resources ready do download. No inputs required.
    """
    _LOGGER.debug("RefGenConf object:\n{}".format(rgc))
    templ_vars = {"request": request, "genomes": rgc[CFG_GENOMES_KEY], "rgc": rgc,
                  "openapi_version": get_openapi_version(app)}
    _LOGGER.debug("merged vars: {}".format(dict(templ_vars, **ALL_VERSIONS)))
    return templates.TemplateResponse("v3/index.html", dict(templ_vars, **ALL_VERSIONS))


@router.get("/asset/{genome}/{asset}/splash")
async def asset_splash_page(request: Request, genome: str = g, asset: str = a, tag: Optional[str] = tq):
    """
    Returns an asset splash page
    """
    tag = tag or rgc.get_default_tag(genome, asset)  # returns 'default' for nonexistent genome/asset; no need to catch
    links_dict = {OPERATION_IDS["v3_asset"][oid]: path.format(genome=genome, asset=asset, tag=tag)
                  for oid, path in map_paths_by_id(app.openapi()).items() if oid in OPERATION_IDS["v3_asset"].keys()}
    templ_vars = {"request": request, "genome": genome, "asset": asset,
                  "tag": tag, "rgc": rgc, "prp": parse_registry_path, "links_dict": links_dict,
                  "openapi_version": get_openapi_version(app)}
    _LOGGER.debug("merged vars: {}".format(dict(templ_vars, **ALL_VERSIONS)))
    return templates.TemplateResponse("v3/asset.html", dict(templ_vars, **ALL_VERSIONS))


@router.get("/genomes")
async def list_available_genomes():
    """
    Returns a list of genomes this server holds at least one asset for. No inputs required.
    """
    _LOGGER.info("serving genomes string: '{}'".format(rgc.genomes_str()))
    return rgc.genomes_list()


@router.get("/assets", operation_id=API_VERSION + API_ID_ASSETS)
async def list_available_assets():
    """
    Returns a list of all assets that can be downloaded. No inputs required.
    """
    ret_dict = rgc.list(include_tags=True)
    _LOGGER.info("serving assets dict: {}".format(ret_dict))
    return ret_dict


@router.get("/asset/{genome}/{asset}/archive",
            operation_id=API_VERSION + API_ID_ARCHIVE)
async def download_asset(genome: str = g, asset: str = a, tag: Optional[str] = tq):
    """
    Returns an archive. Requires the genome name and the asset name as an input.

    Optionally, 'tag' query parameter can be specified to get a tagged asset archive. Default tag is returned otherwise.
    """
    tag = tag or rgc.get_default_tag(genome, asset)  # returns 'default' for nonexistent genome/asset; no need to catch
    file_name = "{}__{}{}".format(asset, tag, ".tgz")
    path, remote = get_datapath_for_genome(rgc, dict(genome=genome, file_name=file_name))
    _LOGGER.info("file source: {}".format(path))
    if remote:
        _LOGGER.info("redirecting to URL: '{}'".format(path))
        return RedirectResponse(path)
    _LOGGER.info("serving asset file: '{}'".format(path))
    if os.path.isfile(path):
        return FileResponse(path, filename=file_name, media_type="application/octet-stream")
    else:
        msg = MSG_404.format("asset ({})".format(asset))
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)


@router.get("/asset/{genome}/{asset}/default_tag",
            operation_id=API_VERSION + API_ID_DEFAULT_TAG)
async def get_asset_default_tag(genome: str = g, asset: str = a):
    """
    Returns the default tag name. Requires genome name and asset name as an input.
    """
    return rgc.get_default_tag(genome, asset)


@router.get("/asset/{genome}/{asset}/{tag}/asset_digest",
            operation_id=API_VERSION + API_ID_DIGEST)
async def get_asset_digest(genome: str = g, asset: str = a, tag: str = t):
    """
    Returns the asset digest. Requires genome name asset name and tag name as an input.
    """
    try:
        return rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset][CFG_ASSET_TAGS_KEY][tag][CFG_ASSET_CHECKSUM_KEY]
    except KeyError:
        msg = MSG_404.format("genome/asset:tag combination ({}/{}:{})".format(genome, asset, tag))
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)


@router.get("/asset/{genome}/{asset}/{tag}/archive_digest",
            operation_id=API_VERSION + API_ID_ARCHIVE_DIGEST)
async def get_asset_digest(genome: str = g, asset: str = a, tag: str = t):
    """
    Returns the archive digest. Requires genome name asset name and tag name as an input.
    """
    try:
        return rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset][CFG_ASSET_TAGS_KEY][tag][CFG_ARCHIVE_CHECKSUM_KEY]
    except KeyError:
        msg = MSG_404.format("genome/asset:tag combination ({}/{}:{})".format(genome, asset, tag))
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)


@router.get("/asset/{genome}/{asset}/log",
            operation_id=API_VERSION + API_ID_LOG)
async def download_asset_build_log(genome: str = g, asset: str = a, tag: Optional[str] = tq):
    """
    Returns a build log. Requires the genome name and the asset name as an input.

    Optionally, 'tag' query parameter can be specified to get a tagged asset archive. Default tag is returned otherwise.
    """
    tag = tag or rgc.get_default_tag(genome, asset)  # returns 'default' for nonexistent genome/asset; no need to catch
    file_name = TEMPLATE_LOG.format(asset, tag)
    path, remote = get_datapath_for_genome(rgc, dict(genome=genome, file_name=file_name))
    if remote:
        _LOGGER.info("redirecting to URL: '{}'".format(path))
        return RedirectResponse(path)
    _LOGGER.info("serving build log file: '{}'".format(path))
    if os.path.isfile(path):
        return FileResponse(path, filename=file_name, media_type="application/octet-stream")
    else:
        msg = MSG_404.format("asset ({})".format(asset))
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)


@router.get("/asset/{genome}/{asset}/recipe",
            operation_id=API_VERSION + API_ID_RECIPE)
async def download_asset_build_recipe(genome: str = g, asset: str = a, tag: Optional[str] = tq):
    """
    Returns a build recipe. Requires the genome name and the asset name as an input.

    Optionally, 'tag' query parameter can be specified to get a tagged asset archive. Default tag is returned otherwise.
    """
    tag = tag or rgc.get_default_tag(genome, asset)  # returns 'default' for nonexistent genome/asset; no need to catch
    file_name = TEMPLATE_RECIPE_JSON.format(asset, tag)
    path, remote = get_datapath_for_genome(rgc, dict(genome=genome, file_name=file_name))
    if remote:
        _LOGGER.info("redirecting to URL: '{}'".format(path))
        return RedirectResponse(path)
    _LOGGER.info("serving build log file: '{}'".format(path))
    if os.path.isfile(path):
        import json
        with open(path, 'r') as f:
            recipe = json.load(f)
        return JSONResponse(recipe)
    else:
        msg = MSG_404.format("asset ({})".format(asset))
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)


@router.get("/asset/{genome}/{asset}",
            operation_id=API_VERSION + API_ID_ASSET_ATTRS)
async def download_asset_attributes(genome: str = g, asset: str = a, tag: Optional[str] = tq):
    """
    Returns a dictionary of asset attributes, like archive size, archive digest etc.
    Requires the genome name and the asset name as an input.
    Optionally, 'tag' query parameter can be specified to get a tagged asset attributes.
    """
    tag = tag or rgc.get_default_tag(genome, asset)  # returns 'default' for nonexistent genome/asset; no need to catch
    try:
        attrs = rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset][CFG_ASSET_TAGS_KEY][tag]
        _LOGGER.info("attributes returned for {}/{}:{}: \n{}".format(genome, asset, tag, attrs))
        return attrs
    except KeyError:
        msg = MSG_404.format("genome/asset:tag combination ({}/{}:{})".format(genome, asset, tag))
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)


@router.get("/genome/{genome}/genome_digest")
async def download_genome_digest(genome: str = g):
    """
    Returns the genome digest. Requires the genome name as an input
    """
    try:
        digest = rgc[CFG_GENOMES_KEY][genome][CFG_CHECKSUM_KEY]
        _LOGGER.info("digest returned for '{}': {}".format(genome, digest))
        return digest
    except KeyError:
        msg = MSG_404.format("genome ({})".format(genome))
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)


@router.get("/genome/{genome}",
            operation_id=API_VERSION + API_ID_GENOME_ATTRS)
async def download_genome_attributes(genome: str = g):
    """
    Returns a dictionary of genome attributes, like archive size, archive digest etc.
    Requires the genome name name as an input.
    """
    try:
        attrs = rgc.get_genome_attributes(genome)
        _LOGGER.info("attributes returned for genome '{}': \n{}".format(genome, str(attrs)))
        return attrs
    except KeyError:
        msg = MSG_404.format("genome ({})".format(genome))
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)


@router.get("/genomes/{asset}")
async def list_genomes_by_asset(asset: str = a):
    """
    Returns a list of genomes that have the requested asset defined. Requires the asset name as an input.
    """
    genomes = rgc.list_genomes_by_asset(asset)
    _LOGGER.info("serving genomes by '{}' asset: {}".format(asset, genomes))
    return genomes


@router.get("/alias/genome_digest/{alias}",
            operation_id=API_VERSION + API_ID_ALIAS_DIGEST)
async def get_genome_alias_digest(alias: str = a):
    """
    Returns the genome digest. Requires the genome name as an input
    """
    try:
        digest = rgc.get_genome_alias_digest(alias=alias)
        _LOGGER.info("digest returned for '{}': {}".format(alias, digest))
        return digest
    except (KeyError, UndefinedAliasError):
        msg = MSG_404.format("alias ({})".format(alias))
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)


@router.get("/alias/alias/{genome_digest}", operation_id=API_VERSION + API_ID_ALIAS_ALIAS)
async def get_genome_alias(genome_digest: str = g):
    """
    Returns the genome digest. Requires the genome name as an input
    """
    try:
        alias = rgc[CFG_GENOMES_KEY][genome_digest][CFG_ALIASES_KEY]
        _LOGGER.info("alias returned for '{}': {}".format(genome_digest, alias))
        return alias
    except (KeyError, UndefinedAliasError):
        msg = MSG_404.format("genome ({})".format(genome_digest))
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)

