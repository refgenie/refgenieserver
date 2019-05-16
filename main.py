from fastapi import FastAPI, HTTPException
import os
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import Response
from starlette.responses import FileResponse
from starlette.responses import StreamingResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

import asyncio

from refgenconf import RefGenomeConfiguration, select_genome_config
import uvicorn
from _version import __version__ as v
from const import BASE_FOLDER, BASE_URL
from helpers import Parser

app = FastAPI()


app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# This can be used to add a simple file server to server files in a directory
# You access these files with e.g. http://localhost/static
# app.mount("/static", StaticFiles(directory=base_folder), name="static")


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
    local_file = "{base}/{genome}/{asset}.{ext}".format(base=BASE_FOLDER, genome=genome, asset=asset, ext=ext)
    print("local file: ", local_file)
    # url = "{base}/{genome}/{asset}.{ext}".format(base=BASE_URL, genome="example_data", asset="rCRS.fa.gz", ext=ext)
    if os.path.isfile(local_file):
        return FileResponse(local_file)
    else:
        print("local file: ", local_file)
        raise HTTPException(status_code=404, detail="No such asset on server")


if __name__ == "__main__":
    parser = Parser()
    args = parser.parse_args()
    rgc = RefGenomeConfiguration(select_genome_config(args.config))
    print("Genomes: {}".format(rgc.list_genomes()))
    print("Indexes:\n{}".format(rgc.list_assets()))
    print(rgc.idx())
    uvicorn.run(app, host="localhost", port=args.port)