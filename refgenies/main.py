import os
import uvicorn
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import Response
from starlette.responses import FileResponse
from starlette.responses import StreamingResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from fastapi import FastAPI, HTTPException
from refgenconf import RefGenomeConfiguration, select_genome_config

from ._version import __version__ as v
from .const import *
from .helpers import Parser

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
    # print(rgc.genomes)
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

# TODO: remove the endpoint and place the text on the landing page instead
@app.get("/what")
async def what(request: Request):
    return templates.TemplateResponse("what.html", {"request": request, "version": v})


def main():
    global rgc
    parser = Parser()
    args = parser.parse_args()
    rgc = RefGenomeConfiguration(select_genome_config(args.config))
    uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    main()
