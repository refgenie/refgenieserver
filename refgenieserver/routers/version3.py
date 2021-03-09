from starlette.responses import FileResponse, JSONResponse, RedirectResponse
from starlette.requests import Request
from fastapi import HTTPException, APIRouter, Path, Query
from typing import Optional
from copy import copy


from ubiquerg import parse_registry_path
from refgenconf.refgenconf import map_paths_by_id
from yacman import UndefinedAliasError, IK

from ..const import *
from ..main import rgc, templates, _LOGGER, app
from ..helpers import get_openapi_version, get_datapath_for_genome, safely_get_example
from ..data_models import Tag, Genome, Dict, List

ex_alias = safely_get_example(
    rgc,
    "genome digest",
    "genomes_list",
    "2230c535660fb4774114bfa966a62f823fdb6d21acf138d4",
)
ex_digest = safely_get_example(
    rgc, "genome alias", "get_genome_alias_digest", "hg38", alias=ex_alias
)
ex_asset = safely_get_example(
    rgc, "asset", "list_assets_by_genome", "fasta", genome=ex_alias
)

router = APIRouter()

# API query path definitions
g = Path(
    ...,
    description="Genome digest",
    regex=r"^\w+$",
    max_length=48,
    min_length=48,
    example=ex_digest,
)
al = Path(
    ...,
    description="Genome alias",
    regex=r"^\S+$",
    example=ex_alias,
)
a = Path(
    ...,
    description="Asset name",
    regex=r"^\S+$",
    example=ex_asset,
)
t = Path(
    ...,
    description="Tag name",
    regex=r"^\S+$",
    example=DEFAULT_TAG,
)

# API query parameter definitions
tq = Query(
    None,
    description="Tag name",
    regex=r"^\S+$",
)

api_version_tags = [API3_ID]


@router.get("/", tags=api_version_tags)
@router.get("/index", tags=api_version_tags)
async def index(request: Request):
    """
    Returns a landing page HTML with the server resources ready do download.
    No inputs required.
    """
    _LOGGER.debug(f"RefGenConf object:\n{rgc}")
    templ_vars = {
        "request": request,
        "genomes": rgc[CFG_GENOMES_KEY],
        "rgc": rgc,
        "openapi_version": get_openapi_version(app),
        "columns": ["aliases", "digest", "description", "fasta asset", "# assets"],
    }
    return templates.TemplateResponse("v3/index.html", dict(templ_vars, **ALL_VERSIONS))


@router.get("/genomes/splash/{genome}", tags=api_version_tags)
async def genome_splash_page(request: Request, genome: str = g):
    """
    Returns a genome splash page
    """
    templ_vars = {
        "openapi_version": get_openapi_version(app),
        "genome": genome,
        "genome_dict": rgc[CFG_GENOMES_KEY][genome],
        "request": request,
        "columns": [
            "download",
            "asset name:tag",
            "asset description",
            "asset/archive size",
            "archive digest",
        ],
    }
    _LOGGER.debug(f"merged vars: {dict(templ_vars, **ALL_VERSIONS)}")
    return templates.TemplateResponse(
        "v3/genome.html", dict(templ_vars, **ALL_VERSIONS)
    )


@router.get("/assets/splash/{genome}/{asset}", tags=api_version_tags)
async def asset_splash_page(
    request: Request, genome: str = g, asset: str = a, tag: Optional[str] = tq
):
    """
    Returns an asset splash page
    """
    tag = tag or rgc.get_default_tag(
        genome, asset
    )  # returns 'default' for nonexistent genome/asset; no need to catch
    links_dict = {
        OPERATION_IDS["v3_asset"][oid]: path.format(genome=genome, asset=asset, tag=tag)
        for oid, path in map_paths_by_id(app.openapi()).items()
        if oid in OPERATION_IDS["v3_asset"].keys()
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
    _LOGGER.debug(f"merged vars: {dict(templ_vars, **ALL_VERSIONS)}")
    return templates.TemplateResponse("v3/asset.html", dict(templ_vars, **ALL_VERSIONS))


@router.get("/genomes/list", response_model=List[str], tags=api_version_tags)
async def list_available_genomes():
    """
    Returns a list of **genome digests** this server serves at least one asset for.
    """
    _LOGGER.info("serving genomes list")
    return list(rgc.genomes[IK]["aliases_raw"].keys())


@router.get(
    "/genomes/alias_dict",
    response_model=Dict[str, List[str]],
    tags=api_version_tags,
    operation_id=API_VERSION + API_ID_ALIASES_DICT,
)
async def get_alias_dict():
    """
    Returns a dictionary of lists of aliases keyed by the respective genome digests.
    """
    _LOGGER.info("serving genomes alias dict")
    return rgc.genomes[IK]["aliases_raw"]


@router.get(
    "/assets/list",
    operation_id=API_VERSION + API_ID_ASSETS,
    response_model=Dict[str, List[str]],
    tags=api_version_tags,
)
async def list_available_assets(
    includeSeekKeys: Optional[bool] = Query(
        False, description="Whether to include seek keys in the response"
    )
):
    """
    Returns a list of assets that can be downloaded, keyed by the respective genome digests.
    """
    ret_dict = (
        rgc.list(include_tags=True) if includeSeekKeys else rgc.list_assets_by_genome()
    )
    digest_dict = {
        rgc.get_genome_alias_digest(alias=alias): assets
        for alias, assets in ret_dict.items()
    }
    _LOGGER.info(f"serving assets dict: {digest_dict}")
    return digest_dict


@router.get(
    "/assets/archive/{genome}/{asset}",
    operation_id=API_VERSION + API_ID_ARCHIVE,
    tags=api_version_tags,
)
async def download_asset(genome: str = g, asset: str = a, tag: Optional[str] = tq):
    """
    Returns an archive. Requires the genome name and the asset name as an input.

    Optionally, 'tag' query parameter can be specified to get a tagged asset archive.
    Default tag is returned otherwise.
    """
    tag = tag or rgc.get_default_tag(
        genome, asset
    )  # returns 'default' for nonexistent genome/asset; no need to catch
    file_name = f"{asset}__{tag}.tgz"
    path, remote = get_datapath_for_genome(
        rgc, dict(genome=genome, file_name=file_name)
    )
    _LOGGER.info(f"file source: {path}")
    if remote:
        _LOGGER.info(f"redirecting to URL: '{path}'")
        return RedirectResponse(path)
    _LOGGER.info(f"serving asset file: '{path}'")
    if os.path.isfile(path):
        return FileResponse(
            path, filename=file_name, media_type="application/octet-stream"
        )
    else:
        msg = MSG_404.format(f"asset ({asset})")
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)


@router.get(
    "/assets/default_tag/{genome}/{asset}",
    operation_id=API_VERSION + API_ID_DEFAULT_TAG,
    response_model=str,
    tags=api_version_tags,
)
async def get_asset_default_tag(genome: str = g, asset: str = a):
    """
    Returns the default tag name. Requires genome name and asset name as an input.
    """
    return rgc.get_default_tag(genome, asset)


@router.get(
    "/assets/asset_digest/{genome}/{asset}",
    operation_id=API_VERSION + API_ID_DIGEST,
    response_model=str,
    tags=api_version_tags,
)
async def get_asset_digest(genome: str = g, asset: str = a, tag: Optional[str] = tq):
    """
    Returns the asset digest. Requires genome name asset name and tag name as an input.
    """
    tag = tag or DEFAULT_TAG
    try:
        return rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset][CFG_ASSET_TAGS_KEY][
            tag
        ][CFG_ASSET_CHECKSUM_KEY]
    except KeyError:
        msg = MSG_404.format(f"genome/asset:tag combination ({genome}/{asset}:{tag})")
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)


@router.get(
    "/assets/archive_digest/{genome}/{asset}",
    operation_id=API_VERSION + API_ID_ARCHIVE_DIGEST,
    response_model=str,
    tags=api_version_tags,
)
async def get_archive_digest(genome: str = g, asset: str = a, tag: Optional[str] = tq):
    """
    Returns the archive digest. Requires genome name asset name and tag name as an input.
    """
    tag = tag or DEFAULT_TAG
    try:
        return rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset][CFG_ASSET_TAGS_KEY][
            tag
        ][CFG_ARCHIVE_CHECKSUM_KEY]
    except KeyError:
        msg = MSG_404.format(f"genome/asset:tag combination ({genome}/{asset}:{tag})")
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)


@router.get(
    "/assets/log/{genome}/{asset}",
    operation_id=API_VERSION + API_ID_LOG,
    tags=api_version_tags,
)
async def download_asset_build_log(
    genome: str = g, asset: str = a, tag: Optional[str] = tq
):
    """
    Returns a build log. Requires the genome name and the asset name as an input.

    Optionally, 'tag' query parameter can be specified to get a tagged asset archive.
    Default tag is returned otherwise.
    """
    tag = tag or rgc.get_default_tag(
        genome, asset
    )  # returns 'default' for nonexistent genome/asset; no need to catch
    file_name = TEMPLATE_LOG.format(asset, tag)
    path, remote = get_datapath_for_genome(
        rgc, dict(genome=genome, file_name=file_name)
    )
    if remote:
        _LOGGER.info(f"redirecting to URL: '{path}'")
        return RedirectResponse(path)
    _LOGGER.info(f"serving build log file: '{path}'")
    if os.path.isfile(path):
        return FileResponse(
            path, filename=file_name, media_type="application/octet-stream"
        )
    else:
        msg = MSG_404.format(f"asset ({asset})")
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)


@router.get(
    "/assets/recipe/{genome}/{asset}",
    operation_id=API_VERSION + API_ID_RECIPE,
    tags=api_version_tags,
)
async def download_asset_build_recipe(
    genome: str = g, asset: str = a, tag: Optional[str] = tq
):
    """
    Returns a build recipe. Requires the genome name and the asset name as an input.

    Optionally, 'tag' query parameter can be specified to get a tagged asset archive.
    Default tag is returned otherwise.
    """
    tag = tag or rgc.get_default_tag(
        genome, asset
    )  # returns 'default' for nonexistent genome/asset; no need to catch
    file_name = TEMPLATE_RECIPE_JSON.format(asset, tag)
    path, remote = get_datapath_for_genome(
        rgc, dict(genome=genome, file_name=file_name)
    )
    if remote:
        _LOGGER.info(f"redirecting to URL: '{path}'")
        return RedirectResponse(path)
    _LOGGER.info(f"serving build log file: '{path}'")
    if os.path.isfile(path):
        import json

        with open(path, "r") as f:
            recipe = json.load(f)
        return JSONResponse(recipe)
    else:
        msg = MSG_404.format(f"asset ({asset})")
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)


@router.get(
    "/assets/attrs/{genome}/{asset}",
    operation_id=API_VERSION + API_ID_ASSET_ATTRS,
    response_model=Tag,
    tags=api_version_tags,
)
async def download_asset_attributes(
    genome: str = g, asset: str = a, tag: Optional[str] = tq
):
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
            # this API version we need remove the old entry from served attrs
            del attrs_copy[CFG_LEGACY_ARCHIVE_CHECKSUM_KEY]
        _LOGGER.info(f"attributes returned for {genome}/{asset}:{tag}: \n{attrs_copy}")
        return attrs_copy
    except KeyError:
        msg = MSG_404.format(f"genome/asset:tag combination ({genome}/{asset}:{tag})")
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)


@router.get(
    "/genomes/attrs/{genome}",
    operation_id=API_VERSION + API_ID_GENOME_ATTRS,
    response_model=Dict[str, str],
    tags=api_version_tags,
)
async def download_genome_attributes(genome: str = g):
    """
    Returns a dictionary of genome attributes, like archive size, archive digest etc.
    Requires the genome name name as an input.
    """
    try:
        attrs = rgc.get_genome_attributes(genome)
        _LOGGER.info(f"attributes returned for genome '{genome}': \n{attrs}")
        return attrs
    except KeyError:
        msg = MSG_404.format(f"genome ({genome})")
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)


@router.get(
    "/genomes/by_asset/{asset}", response_model=List[str], tags=api_version_tags
)
async def list_genomes_by_asset(asset: str = a):
    """
    Returns a list of genomes that have the requested asset defined.
    Requires the asset name as an input.
    """
    genomes = rgc.list_genomes_by_asset(asset)
    _LOGGER.info(f"serving genomes by '{asset}' asset: {genomes}")
    return genomes


@router.get(
    "/genomes/genome_digest/{alias}",
    operation_id=API_VERSION + API_ID_ALIAS_DIGEST,
    response_model=str,
    tags=api_version_tags,
)
async def get_genome_alias_digest(alias: str = al):
    """
    Returns the genome digest. Requires the genome name as an input
    """
    try:
        digest = rgc.get_genome_alias_digest(alias=alias)
        _LOGGER.info(f"digest returned for '{alias}': {digest}")
        return digest
    except (KeyError, UndefinedAliasError):
        msg = MSG_404.format(f"alias ({alias})")
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)


@router.get(
    "/genomes/aliases/{genome_digest}",
    operation_id=API_VERSION + API_ID_ALIAS_ALIAS,
    response_model=List[str],
    tags=api_version_tags,
)
async def get_genome_alias(genome_digest: str = g):
    """
    Returns the genome digest. Requires the genome name as an input
    """
    try:
        alias = rgc[CFG_GENOMES_KEY][genome_digest][CFG_ALIASES_KEY]
        _LOGGER.info(f"alias returned for '{genome_digest}': {alias}")
        return alias
    except (KeyError, UndefinedAliasError):
        msg = MSG_404.format(f"genome ({genome_digest})")
        _LOGGER.warning(msg)
        raise HTTPException(status_code=404, detail=msg)
