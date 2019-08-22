import sys
import uvicorn
import logmuse
from starlette.requests import Request
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from fastapi import FastAPI, HTTPException
from refgenconf import RefGenConf, select_genome_config

from .const import *
from .helpers import build_parser
from .server_builder import archive
import logging

app = FastAPI()
app.mount("/" + STATIC_DIRNAME, StaticFiles(directory=STATIC_PATH), name=STATIC_DIRNAME)
templates = Jinja2Templates(directory=TEMPLATES_PATH)

# This can be used to add a simple file server to server files in a directory
# You access these files with e.g. http://localhost/static
# app.mount("/static", StaticFiles(directory=base_folder), name="static")
global rgc
_LOGGER = logging.getLogger(PKG_NAME)


@app.get("/")
@app.get("/index")
async def index(request: Request):
    """
    Returns a landing page HTML with the server resources ready do download. No inputs required.
    """
    _LOGGER.debug("RefGenConf object:\n{}".format(rgc))
    vars = {"request": request, "genomes": rgc[CFG_GENOMES_KEY], "rgc": rgc[CFG_GENOMES_KEY]}
    _LOGGER.debug("merged vars: {}".format(dict(vars, **ALL_VERSIONS)))
    return templates.TemplateResponse("index.html", dict(vars, **ALL_VERSIONS))


@app.get("/genomes")
def list_available_genomes():
    """
    Returns a list of genomes this server holds at least one asset for. No inputs required.
    """
    _LOGGER.info("serving genomes string: '{}'".format(rgc.genomes_str()))
    return rgc.genomes_list()


@app.get("/assets")
def list_available_assets():
    """
    Returns a list of all assets that can be downloaded. No inputs required.
    """
    _LOGGER.info("serving assets dict: '{}'".format(rgc.assets_dict()))
    return rgc.assets_dict()


@app.get("/asset/{genome}/{asset}/archive")
async def download_asset(genome: str, asset: str, tag: str = None):
    """
    Returns an archive. Requires the genome name and the asset name as an input.

    Optionally, 'tag' query parameter can be specified to get a tagged asset archive.
    """
    tag = tag or rgc.get_default_tag(genome, asset)  # returns 'default' for nonexistent genome/asset; no need to catch
    file_name = "{}__{}{}".format(asset, tag, TGZ["ext"])
    asset_file = "{base}/{genome}/{file_name}".format(base=BASE_DIR, genome=genome, file_name=file_name)
    _LOGGER.info("serving asset file: '{}'".format(asset_file))
    if os.path.isfile(asset_file):
        return FileResponse(asset_file, filename=file_name, media_type="application/octet-stream")
    else:
        _LOGGER.warning(MSG_404.format("asset"))
        raise HTTPException(status_code=404, detail=MSG_404.format("asset"))


@app.get("/asset/{genome}/{asset}/default_tag")
async def download_asset(genome: str, asset: str):
    """
    Returns the default tag name. Requires genome name and asset name as an input.
    """
    return rgc.get_default_tag(genome, asset)


@app.get("/asset/{genome}/{asset}")
def download_asset_attributes(genome: str, asset: str, tag: str = None):
    """
    Returns a dictionary of asset attributes, like archive size, archive checksum etc.
    Requires the genome name and the asset name as an input.
    Optionally, 'tag' query parameter can be specified to get a tagged asset attributes.
    """
    tag = tag or rgc.get_default_tag(genome, asset)  # returns 'default' for nonexistent genome/asset; no need to catch
    try:
        attrs = rgc[CFG_GENOMES_KEY][genome][CFG_ASSETS_KEY][asset][tag]
        _LOGGER.info("attributes returned for {}/{}:{}: \n{}".format(genome, asset, tag, attrs))
        return attrs
    except KeyError:
        _LOGGER.warning(_LOGGER.warning(MSG_404.format("genome, asset or tag")))
        raise HTTPException(status_code=404, detail=MSG_404.format("genome, asset or tag"))


@app.get("/genome/{genome}/genome_checksum")
async def download_genome_checksum(genome: str):
    """
    Returns the genome checksum. Requires the genome name as an input
    """
    try:
        checksum = rgc[CFG_GENOMES_KEY][genome][CFG_CHECKSUM_KEY]
        _LOGGER.info("checksum returned for '{}': {}".format(genome, checksum))
        return checksum
    except KeyError:
        _LOGGER.warning(MSG_404.format("genome"))
        raise HTTPException(status_code=404, detail=MSG_404.format("genome"))


@app.get("/genome/{genome}")
async def download_genome_attributes(genome: str):
    """
    Returns a dictionary of genome attributes, like archive size, archive checksum etc.
    Requires the genome name name as an input.
    """
    try:
        attrs = rgc.get_genome_attributes(genome)
        _LOGGER.info("attributes returned for genome '{}': \n{}".format(genome, str(attrs)))
        return attrs
    except KeyError:
        _LOGGER.warning(MSG_404.format("genome"))
        raise HTTPException(status_code=404, detail=MSG_404.format("genome or asset"))


@app.get("/genomes/{asset}")
def list_genomes_by_asset(asset: str):
    """
    Returns a list of genomes that have the requested asset defined. Requires the asset name as an input.
    """
    genomes = rgc.list_genomes_by_asset(asset)
    _LOGGER.info("serving genomes by '{}' asset: {}".format(asset, genomes))
    return genomes


def main():
    global rgc
    parser = build_parser()
    args = parser.parse_args()
    logger_args = dict(name=PKG_NAME, fmt=LOG_FORMAT, level=5) if args.debug else dict(name=PKG_NAME, fmt=LOG_FORMAT)
    _LOGGER = logmuse.setup_logger(**logger_args)
    selected_cfg = select_genome_config(args.config)
    rgc = RefGenConf(selected_cfg)
    assert len(rgc) > 0, "You must provide a config file or set the '{}' " \
                         "environment variable".format(", ".join(CFG_ENV_VARS))
    if args.command == "archive":
        archive(rgc, args.genome, args.asset, args.force, selected_cfg)
    elif args.command == "serve":
        uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        _LOGGER.info("Program canceled by user")
        sys.exit(1)
