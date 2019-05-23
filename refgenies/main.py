import os
import sys
import uvicorn
import logmuse
from starlette.requests import Request
from starlette.responses import FileResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from fastapi import FastAPI, HTTPException
from refgenconf import RefGenomeConfiguration, select_genome_config, CONFIG_ENV_VARS

from _version import __version__ as v
from const import *
from helpers import build_parser
from server_builder import archive
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
    _LOGGER.debug("RefGenomeConfiguration object:\n{}".format(rgc))
    vars = {"request": request, "version": v, "genomes": rgc.assets_dict(), "rgc": rgc[CFG_GENOMES_KEY]}
    return templates.TemplateResponse("index.html", vars)


@app.get("/genomes")
def list_available_genomes():
    """
    Returns a list of genomes this server holds at least one asset for. No inputs required.
    """
    _LOGGER.info("serving genomes string: '{}'".format(rgc.genomes_str()))
    return rgc.genomes_list()


@app.get("/assets")
def list_assets_by_genome():
    """
    List all assets that can be downloaded for a given genome.

    - **genome**: 
    """
    _LOGGER.info("serving assets string: '{}'".format(rgc.assets_str()))
    return rgc.assets_dict()


@app.get("/asset/{genome}/{asset}/archive")
def download_asset(genome: str, asset: str):
    file_name = "{}{}".format(asset, TGZ["ext"])
    asset_file = "{base}/{genome}/{file_name}".format(base=rgc[CFG_ARCHIVE_KEY], genome=genome, file_name=file_name)
    _LOGGER.info("serving asset file: '{}'".format(asset_file))
    # url = "{base}/{genome}/{asset}.{ext}".format(base=BASE_URL, genome="example_data", asset="rCRS.fa.gz", ext=ext)
    if os.path.isfile(asset_file):
        return FileResponse(asset_file, filename=file_name)
    else:
        raise HTTPException(status_code=404, detail="No such asset on server")


@app.get("/asset/{genome}/{asset}")
def download_asset_attributes(genome: str, asset: str):
    try:
        attrs = rgc[CFG_GENOMES_KEY][genome][asset]
        _LOGGER.info("attributes returned for asset '{}' and genome '{}': \n{}".format(asset, genome, attrs))
        return attrs
    except KeyError:
        raise HTTPException(status_code=404, detail="No such asset or genome on server")


@app.get("/genome/{genome}")
def download_genome(genome: str):
    file_name = "{}{}".format(genome, TAR["ext"])
    genome_file = "{base}/{file_name}".format(base=rgc[CFG_ARCHIVE_KEY], file_name=file_name)
    _LOGGER.info("serving genome archive: '{}'".format(genome_file))
    # url = "{base}/{genome}/{asset}.{ext}".format(base=BASE_URL, genome="example_data", asset="rCRS.fa.gz", ext=ext)
    if os.path.isfile(genome_file):
        return FileResponse(genome_file, filename=file_name)
    else:
        raise HTTPException(status_code=404, detail="No such genome on server")


@app.get("/genomes/{asset}")
def list_genomes_by_asset(asset: str):
    """
    Returns a list of genomes on this server that define the requested asset
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
    rgc = RefGenomeConfiguration(select_genome_config(args.config))
    assert len(rgc) > 0, "You must provide a config file or set the '{}' " \
                         "environment variable".format(", ".join(CONFIG_ENV_VARS))
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
