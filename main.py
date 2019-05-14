from fastapi import FastAPI
import os
from pydantic import BaseModel
from starlette.requests import Request
from starlette.responses import Response
from starlette.responses import FileResponse
from starlette.responses import StreamingResponse
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

import asyncio

from refgenconf import RefGenomeConfiguration, load_yaml

app = FastAPI()


templates = Jinja2Templates(directory="templates")

print("Ready...")

# Don't error if RESOURCES is not set.
try:
    # First priority: GENOMES variable
    genome_folder = os.environ["GENOMES"]
except:
    try:
        # Second priority: RESOURCES/genomes
        genome_folder = os.path.join(os.environ["RESOURCES"], "genomes")
    except:
        # Otherwise, current directory
        genome_folder = ""

genome_config = os.path.join(genome_folder, "refgenie.yaml")
rgc = RefGenomeConfiguration(load_yaml(genome_config))

# print(rgc)

print("Genomes: {}".format(rgc.list_genomes()))
print("Indexes:\n{}".format(rgc.list_assets()))

print(rgc.idx())

base_url="http://big.databio.org/refgenie_files"
base_folder="/genomes"

# This can be used to add a simple file server to server files in a directory
# You access these files with e.g. http://localhost/static
# app.mount("/static", StaticFiles(directory=base_folder), name="static")

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/assets")
async def links(request: Request):
    print(rgc.refgenomes)
    return templates.TemplateResponse("list.html", {"request": request, "genomes": rgc.idx()})

@app.get("/items/{id}")
async def read_item(request: Request, id: str):
    return templates.TemplateResponse("item.html", {"request": request, "id": id})


@app.get("/genomes")
def list_available_genomes():
    print("Genomes: {}".format(rgc.list_genomes()))
    return rgc.list_genomes()



@app.get("/genome/{genome}")
def list_available_assets():
    return rgc.list_indexes()




@app.get("/asset/{genome}/{asset}")
def download_asset(genome: str, asset: str):
    local_file = "{base}/{genome}/{asset}.tar".format(base=base_folder, genome=genome, asset=asset)
    print("local file: ", local_file)
    url = "{base}/{genome}/{asset}.tar".format(base=base_url, genome="example_data", asset="rCRS.fa.gz")
    if os.path.isfile(local_file):
        return FileResponse(local_file)
    else:
        print("local file: ", local_file)
        return {"error": "No such index on the server."}



