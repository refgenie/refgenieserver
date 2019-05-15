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

from refgenconf import RefGenomeConfiguration, load_genome_config

app = FastAPI()


templates = Jinja2Templates(directory="templates")

print("Ready...")



# somehow get genome_config from args.genome_config
genome_config = os.path.join("refgenie.yaml")

rgc = RefGenomeConfiguration(load_genome_config(genome_config))

print("Genomes: {}".format(rgc.list_genomes()))
print("Indexes:\n{}".format(rgc.list_assets()))

print(rgc.idx())

base_url="http://big.databio.org/refgenie_files"
base_folder="/genomes"

# This can be used to add a simple file server to server files in a directory
# You access these files with e.g. http://localhost/static
# app.mount("/static", StaticFiles(directory=base_folder), name="static")

@app.get("/")
async def list_assets(request: Request):
    print(rgc.genomes)
    return templates.TemplateResponse("list_assets.html", {"request": request, "genomes": rgc.idx()})


@app.get("/genomes")
def list_available_genomes():
    print("Genomes: {}".format(rgc.list_genomes()))
    return rgc.list_genomes()


@app.get("/genome/{genome}")
def list_assets_by_genome():
    return rgc.list_assets()


@app.get("/asset/{genome}/{asset}")
def download_asset(genome: str, asset: str):
    local_file = "{base}/{genome}/{asset}.tar".format(base=base_folder, genome=genome, asset=asset)
    print("local file: ", local_file)
    url = "{base}/{genome}/{asset}.tar".format(base=base_url, genome="example_data", asset="rCRS.fa.gz")
    if os.path.isfile(local_file):
        return FileResponse(local_file)
    else:
        print("local file: ", local_file)
        raise HTTPException(status_code=404, detail="No such asset on server")
        



