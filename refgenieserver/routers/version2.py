from starlette.responses import FileResponse
from starlette.requests import Request
from fastapi import HTTPException, APIRouter
from ..const import *
from ..main import rgc, templates, _LOGGER

router = APIRouter()


@router.get("/")
@router.get("/index")
async def index(request: Request):
    """
    Returns a landing page HTML with the server resources ready do download. No inputs required.
    """
    _LOGGER.debug("RefGenConf object:\n{}".format(rgc))
    vars = {"request": request, "genomes": rgc[CFG_GENOMES_KEY], "rgc": rgc[CFG_GENOMES_KEY]}
    _LOGGER.debug("merged vars: {}".format(dict(vars, **ALL_VERSIONS)))
    return templates.TemplateResponse("index.html", dict(vars, **ALL_VERSIONS))


@router.get("/genomes")
def list_available_genomes():
    """
    Returns a list of genomes this server holds at least one asset for. No inputs required.
    """
    _LOGGER.info("serving genomes string: '{}'".format(rgc.genomes_str()))
    return rgc.genomes_list()


@router.get("/assets")
def list_available_assets():
    """
    Returns a list of all assets that can be downloaded. No inputs required.
    """
    ret_dict = rgc.assets_dict(include_tags=True)
    _LOGGER.info("serving assets dict: {}".format(ret_dict))
    return ret_dict


@router.get("/asset/{genome}/{asset}/archive")
async def download_asset(genome: str, asset: str, tag: str = None):
    """
    Returns an archive. Requires the genome name and the asset name as an input.

    Optionally, 'tag' query parameter can be specified to get a tagged asset archive. Default tag is returned otherwise.
    """
    tag = tag or rgc.get_default_tag(genome, asset)  # returns 'default' for nonexistent genome/asset; no need to catch
    file_name = "{}__{}{}".format(asset, tag, ".tgz")
    asset_file = "{base}/{genome}/{file_name}".format(base=BASE_DIR, genome=genome, file_name=file_name)
    _LOGGER.info("serving asset file: '{}'".format(asset_file))
    if os.path.isfile(asset_file):
        return FileResponse(asset_file, filename=file_name, media_type="application/octet-stream")
    else:
        _LOGGER.warning(MSG_404.format("asset"))
        raise HTTPException(status_code=404, detail=MSG_404.format("asset"))


@router.get("/asset/{genome}/{asset}/default_tag")
async def get_asset_default_tag(genome: str, asset: str):
    """
    Returns the default tag name. Requires genome name and asset name as an input.
    """
    return rgc.get_default_tag(genome, asset)


@router.get("/asset/{genome}/{asset}/{tag}/asset_digest")
async def get_asset_digest(genome: str, asset: str, tag: str):
    """
    Returns the asset digest. Requires genome name asset name and tag name as an input.
    """
    try:
        return rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset][CFG_ASSET_TAGS_KEY][tag][CFG_ASSET_CHECKSUM_KEY]
    except KeyError:
        _LOGGER.warning(MSG_404.format("genome/asset:tag combination"))
        raise HTTPException(status_code=404, detail=MSG_404.format("genome/asset:tag combination"))


@router.get("/asset/{genome}/{asset}")
def download_asset_attributes(genome: str, asset: str, tag: str = None):
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
        _LOGGER.warning(_LOGGER.warning(MSG_404.format("genome/asset:tag combination")))
        raise HTTPException(status_code=404, detail=MSG_404.format("genome/asset:tag combination"))


@router.get("/genome/{genome}/genome_digest")
async def download_genome_digest(genome: str):
    """
    Returns the genome digest. Requires the genome name as an input
    """
    try:
        digest = rgc[CFG_GENOMES_KEY][genome][CFG_CHECKSUM_KEY]
        _LOGGER.info("digest returned for '{}': {}".format(genome, digest))
        return digest
    except KeyError:
        _LOGGER.warning(MSG_404.format("genome"))
        raise HTTPException(status_code=404, detail=MSG_404.format("genome"))


@router.get("/genome/{genome}")
async def download_genome_attributes(genome: str):
    """
    Returns a dictionary of genome attributes, like archive size, archive digest etc.
    Requires the genome name name as an input.
    """
    try:
        attrs = rgc.get_genome_attributes(genome)
        _LOGGER.info("attributes returned for genome '{}': \n{}".format(genome, str(attrs)))
        return attrs
    except KeyError:
        _LOGGER.warning(MSG_404.format("genome"))
        raise HTTPException(status_code=404, detail=MSG_404.format("genome"))


@router.get("/genomes/{asset}")
def list_genomes_by_asset(asset: str):
    """
    Returns a list of genomes that have the requested asset defined. Requires the asset name as an input.
    """
    genomes = rgc.list_genomes_by_asset(asset)
    _LOGGER.info("serving genomes by '{}' asset: {}".format(asset, genomes))
    return genomes