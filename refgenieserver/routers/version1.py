from starlette.responses import FileResponse, RedirectResponse
from starlette.requests import Request
from fastapi import HTTPException, APIRouter
from copy import copy

from refgenconf.helpers import replace_str_in_obj

from ..const import *
from ..helpers import preprocess_attrs
from ..main import rgc, templates, _LOGGER, app
from ..helpers import get_openapi_version, get_datapath_for_genome

router = APIRouter()

api_version_tags = [API1_ID]


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


@router.get("/genomes", tags=api_version_tags)
def list_available_genomes():
    """
    Returns a list of genomes this server holds at least one asset for. No inputs required.
    """
    _LOGGER.info("serving genomes string: '{}'".format(rgc.genomes_str()))
    return rgc.genomes_list()


@router.get("/assets", tags=api_version_tags)
def list_available_assets():
    """
    Returns a list of all assets that can be downloaded. No inputs required.
    """
    ret_dict = rgc.list(include_tags=True)
    _LOGGER.info("serving assets dict: {}".format(ret_dict))
    return ret_dict


@router.get("/asset/{genome}/{asset}/archive", tags=api_version_tags)
async def download_asset(genome: str, asset: str, tag: str = None):
    """
    Returns an archive. Requires the genome name and the asset name as an input.

    Since the refgenconf.RefGenConf object structure has changed (tags were introduced),
    the default tag has to be selected behind the scenes
    """
    tag = tag or rgc.get_default_tag(
        genome, asset
    )  # returns 'default' for nonexistent genome/asset; no need to catch
    file_name = "{}__{}{}".format(asset, tag, ".tgz")
    path, remote = get_datapath_for_genome(
        rgc,
        dict(
            genome=rgc.get_genome_alias(digest=genome, fallback=True),
            file_name=file_name,
        ),
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


@router.get("/asset/{genome}/{asset}", tags=api_version_tags)
def download_asset_attributes(genome: str, asset: str):
    """
    Returns a dictionary of asset attributes, like archive size, archive checksum etc.
    Requires the genome name and the asset name as an input.

    Since the refgenconf.RefGenConf object structure has changed (tags were introduced),
    the default tag has to be selected behind the scenes
    """
    try:
        attrs = preprocess_attrs(
            rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset][CFG_ASSET_TAGS_KEY][
                DEFAULT_TAG
            ]
        )
        attrs_copy = copy(attrs)
        if CFG_LEGACY_ARCHIVE_CHECKSUM_KEY in attrs_copy:
            # TODO: remove in future releases
            # new asset archives consist of different file names, so the new
            # archive digest does not match the old archives. Therefore the
            # archiver saves the old archive digest along with the new. So in
            # this API version we need to swap them and remove the old
            # afterwards
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
        _LOGGER.warning(_LOGGER.warning(MSG_404.format("genome, asset or tag")))
        raise HTTPException(
            status_code=404, detail=MSG_404.format("genome, asset or tag")
        )


@router.get("/genomes/{asset}", tags=api_version_tags)
def list_genomes_by_asset(asset: str):
    """
    Returns a list of genomes that have the requested asset defined. Requires the asset name as an input.
    """
    genomes = rgc.list_genomes_by_asset(asset)
    _LOGGER.info("serving genomes by '{}' asset: {}".format(asset, genomes))
    return genomes
