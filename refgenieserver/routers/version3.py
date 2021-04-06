from copy import copy
from datetime import date
from enum import Enum
from typing import Optional

from fastapi import APIRouter, HTTPException, Path, Query, Response
from refgenconf.refgenconf import map_paths_by_id
from starlette.requests import Request
from starlette.responses import FileResponse, RedirectResponse
from ubiquerg import parse_registry_path
from yacman import IK, UndefinedAliasError

from ..const import *
from ..data_models import Dict, List, Tag
from ..helpers import (
    create_asset_file_path,
    get_asset_dir_contents,
    get_datapath_for_genome,
    get_openapi_version,
    is_data_remote,
    safely_get_example,
    serve_file_for_asset,
    serve_json_for_asset,
)
from ..main import _LOGGER, app, rgc, templates

RemoteClassEnum = Enum(
    "RemoteClassEnum",
    {r: r for r in rgc["remotes"]} if is_data_remote(rgc) else {"http": "http"},
)

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
s = Path(
    ...,
    description="Seek key name",
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
current_year = date.today().year


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
        "current_year": current_year,
    }
    return templates.TemplateResponse("v3/index.html", dict(templ_vars, **ALL_VERSIONS))


@router.get(
    "/remotes/dict", tags=api_version_tags, response_model=Dict[str, Dict[str, str]]
)
async def get_remotes_dict():
    """
    Returns the remotes section of the server configuration file
    """
    return rgc["remotes"] if "remotes" in rgc else None


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
        "current_year": current_year,
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

    try:
        asset_dir_contents = get_asset_dir_contents(
            rgc=rgc, genome=genome, asset=asset, tag=tag
        )
    except Exception as e:
        _LOGGER.warning(
            f"Could not determine asset directory contents. Caught error: {str(e)}"
        )
        asset_dir_contents = None

    asset_dir_paths = {}
    if is_data_remote(rgc):
        for remote_key in rgc["remotes"].keys():
            try:
                asset_dir_path = create_asset_file_path(
                    rgc, genome, asset, tag, "dir", remote_key=remote_key
                )
            except Exception as e:
                _LOGGER.warning(
                    f"Could not determine asset directory path. Caught error: {str(e)}"
                )
                asset_dir_path = None
            asset_dir_paths[remote_key] = asset_dir_path

    templ_vars = {
        "request": request,
        "genome": genome,
        "asset": asset,
        "tag": tag,
        "rgc": rgc,
        "prp": parse_registry_path,
        "links_dict": links_dict,
        "current_year": current_year,
        "openapi_version": get_openapi_version(app),
        "asset_dir_contents": asset_dir_contents,
        "asset_dir_paths": asset_dir_paths,
        "is_data_remote": is_data_remote(rgc),
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
        rgc, dict(genome=genome, file_name=file_name), remote_key="http"
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
    "/assets/file_path/{genome}/{asset}/{seek_key}",
    operation_id=API_VERSION + API_ID_ASSET_PATH,
    tags=api_version_tags,
    response_model=str,
)
async def get_asset_file_path(
    genome: str = g,
    asset: str = a,
    seek_key: str = s,
    tag: Optional[str] = tq,
    remoteClass: RemoteClassEnum = Query(
        "http", description="Remote data provider class"
    ),
):
    """
    Returns a path to the unarchived asset file.
    Requires a genome name, an asset name and a seek_key name as an input.

    Optionally, query parameters can be specified:

    - **tag**: to get a tagged asset file path. Default tag is returned if not specified.
    - **remoteClass**: to set a remote data provider class. 'http' is used if not specified.
    """
    if not is_data_remote(rgc):
        _LOGGER.info(
            "No 'remotes' defined in the server genome configuration file. "
            "Serving a local asset file path."
        )
    return Response(
        content=create_asset_file_path(
            rgc, genome, asset, tag, seek_key, remote_key=remoteClass.value
        ),
        media_type="text/plain",
    )


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
    return Response(content=rgc.get_default_tag(genome, asset), media_type="text/plain")


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
        return Response(
            content=rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset][
                CFG_ASSET_TAGS_KEY
            ][tag][CFG_ASSET_CHECKSUM_KEY],
            media_type="text/plain",
        )
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
        return Response(
            content=rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset][
                CFG_ASSET_TAGS_KEY
            ][tag][CFG_ARCHIVE_CHECKSUM_KEY],
            media_type="text/plain",
        )
    except KeyError:
        msg = MSG_404.format(f"genome/asset:tag combination ({genome}/{asset}:{tag})")
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
    return serve_json_for_asset(
        rgc=rgc,
        genome=genome,
        asset=asset,
        tag=tag,
        template=TEMPLATE_RECIPE_JSON,
    )


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
    return serve_file_for_asset(
        rgc=rgc,
        genome=genome,
        asset=asset,
        tag=tag,
        template=TEMPLATE_LOG,
    )


@router.get(
    "/assets/dir_contents/{genome}/{asset}",
    operation_id=API_VERSION + API_ID_CONTENTS,
    tags=api_version_tags,
)
async def download_asset_directory_contents(
    genome: str = g, asset: str = a, tag: Optional[str] = tq
):
    """
    Returns a asset directory tree file.
    Requires the genome name and the asset name as an input.

    Optionally, 'tag' query parameter can be specified to get a tagged asset archive.
    Default tag is returned otherwise.
    """
    return serve_json_for_asset(
        rgc=rgc,
        genome=genome,
        asset=asset,
        tag=tag,
        template=TEMPLATE_ASSET_DIR_CONTENTS,
    )


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
        return Response(content=digest, media_type="text/plain")
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
