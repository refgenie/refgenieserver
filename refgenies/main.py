import os
import sys
import uvicorn
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

app = FastAPI()
app.mount("/" + STATIC_DIRNAME, StaticFiles(directory=STATIC_PATH), name=STATIC_DIRNAME)
templates = Jinja2Templates(directory=TEMPLATES_PATH)

# This can be used to add a simple file server to server files in a directory
# You access these files with e.g. http://localhost/static
# app.mount("/static", StaticFiles(directory=base_folder), name="static")
global rgc


@app.get("/")
@app.get("/index")
async def index(request: Request):
    print(rgc.genomes)
    return templates.TemplateResponse("index.html", {"request": request, "version": v, "genomes": rgc.assets_dict()})


@app.get("/genomes")
def list_available_genomes():
    """
    Returns a list of genomes this server holds at least one asset for. No inputs required.
    """
    print("Genomes: {}".format(rgc.genomes_str()))
    return rgc.genomes_list()


@app.get("/assets")
def list_assets_by_genome():
    """
    List all assets that can be downloaded for a given genome.

    - **genome**: 
    """
    print("Assets: {}".format(rgc.assets_str()))
    return rgc.assets_dict()


@app.get("/asset/{genome}/{asset}")
def download_asset(genome: str, asset: str):
    ext = "tgz"
    asset_file = "{base}/{genome}/{asset}.{ext}".format(base=BASE_FOLDER, genome=genome, asset=asset, ext=ext)
    print("local asset file: ", asset_file)
    # url = "{base}/{genome}/{asset}.{ext}".format(base=BASE_URL, genome="example_data", asset="rCRS.fa.gz", ext=ext)
    if os.path.isfile(asset_file):
        return FileResponse(asset_file)
    else:
        print("local asset file: ", asset_file)
        raise HTTPException(status_code=404, detail="No such asset on server")


@app.get("/genome/{genome}")
def download_genome(genome: str):
    ext = "tar"
    genome_file = "{base}/{genome}.{ext}".format(base=BASE_FOLDER, genome=genome, ext=ext)
    print("local genome file: ", genome_file)
    # url = "{base}/{genome}/{asset}.{ext}".format(base=BASE_URL, genome="example_data", asset="rCRS.fa.gz", ext=ext)
    if os.path.isfile(genome_file):
        return FileResponse(genome_file)
    else:
        print("local genome file: ", genome_file)
        raise HTTPException(status_code=404, detail="No such genome on server")


def main():
    parser = build_parser()
    args = parser.parse_args()
    global rgc
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
        print("Program canceled by user")
        sys.exit(1)
