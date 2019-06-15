import os
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
from .helpers import build_parser, update_stats
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
    vars = {"request": request, "genomes": rgc.assets_dict(), "rgc": rgc[CFG_GENOMES_KEY]}
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
async def download_asset(genome: str, asset: str):
    """
    Returns an archive. Requires the genome name and the asset name as an input.
    """
    file_name = "{}{}".format(asset, TGZ["ext"])
    asset_file = "{base}/{genome}/{file_name}".format(base=BASE_DIR, genome=genome, file_name=file_name)
    _LOGGER.info("serving asset file: '{}'".format(asset_file))
    if os.path.isfile(asset_file):
        update_stats(rgc, genome, asset)
        _LOGGER.info("'{}/{}' download count updated to: {}".format(
            genome, asset, rgc.genomes[genome][asset][DOWNLOADS_COUNT_KEY]))
        return FileResponse(asset_file, filename=file_name, media_type="application/octet-stream")
    else:
        _LOGGER.warning(MSG_404.format("asset"))
        raise HTTPException(status_code=404, detail=MSG_404.format("asset"))


@app.get("/asset/{genome}/{asset}")
def download_asset_attributes(genome: str, asset: str):
    """
    Returns a dictionary of asset attributes, like archive size, archive checksum etc.
    Requires the genome name and the asset name as an input.
    """
    try:
        attrs = rgc[CFG_GENOMES_KEY][genome][asset]
        _LOGGER.info("attributes returned for asset '{}' and genome '{}': \n{}".format(asset, genome, attrs))
        return attrs
    except KeyError:
        _LOGGER.warning(_LOGGER.warning(MSG_404.format("genome or asset")))
        raise HTTPException(status_code=404, detail=MSG_404.format("genome or asset"))


@app.get("/genome/{genome}")
async def download_genome(genome: str):
    """
    Returns a tarball with **all** the archived assets available for the genome. Requires the genome name as an input.
    """
    file_name = "{}{}".format(genome, TAR["ext"])
    genome_file = "{base}/{file_name}".format(base=rgc[CFG_ARCHIVE_KEY], file_name=file_name)
    _LOGGER.info("serving genome archive: '{}'".format(genome_file))
    # url = "{base}/{genome}/{asset}.{ext}".format(base=BASE_URL, genome="example_data", asset="rCRS.fa.gz", ext=ext)
    if os.path.isfile(genome_file):
        return FileResponse(genome_file, filename=file_name, media_type="application/octet-stream")
    else:
        _LOGGER.warning(MSG_404.format("genome"))
        raise HTTPException(status_code=404, detail=MSG_404.format("genome"))


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
    rgc = RefGenConf(select_genome_config(args.config))
    assert len(rgc) > 0, "You must provide a config file or set the '{}' " \
                         "environment variable".format(", ".join(CFG_ENV_VARS))
    if args.command == "archive":
        archive(rgc, args)
    elif args.command == "serve":
        uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        _LOGGER.info("Program canceled by user")
        sys.exit(1)
