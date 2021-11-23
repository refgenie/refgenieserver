import sys

import logmuse
import uvicorn
from fastapi import FastAPI
from refgenconf import RefGenConf, select_genome_config
from refgenconf.const import CFG_ENV_VARS, PRIVATE_API
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
from ubiquerg import parse_registry_path

from .const import *
from .helpers import build_parser, purge_nonservable
from .server_builder import archive

app = FastAPI(
    title=PKG_NAME,
    description="a web interface and RESTful API for reference genome assets",
    version=server_v,
    openapi_tags=TAGS_METADATA,
)

app.mount("/" + STATIC_DIRNAME, StaticFiles(directory=STATIC_PATH), name=STATIC_DIRNAME)
templates = Jinja2Templates(directory=TEMPLATES_PATH)
templates.env.filters["os_path_join"] = lambda paths: os.path.join(*paths)


def main():
    global rgc, _LOGGER
    parser = build_parser()
    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        print("No subcommand given")
        sys.exit(1)
    logger_args = (
        dict(name=PKG_NAME, fmt=LOG_FORMAT, level=5)
        if args.debug
        else dict(name=PKG_NAME, fmt=LOG_FORMAT)
    )
    _LOGGER = logmuse.setup_logger(**logger_args)
    selected_cfg = select_genome_config(args.config)
    assert (
        selected_cfg is not None
    ), "You must provide a config file or set the {} environment variable".format(
        "or ".join(CFG_ENV_VARS)
    )
    # this RefGenConf object will be used in the server, so it's read-only
    rgc = RefGenConf(filepath=selected_cfg, writable=False)
    if args.command == "archive":
        arp = (
            [parse_registry_path(x) for x in args.asset_registry_paths]
            if args.asset_registry_paths is not None
            else None
        )
        archive(
            rgc,
            arp,
            args.force,
            args.remove,
            selected_cfg,
            args.genomes_desc,
            map=args.map,
            reduce=args.reduce,
        )
    elif args.command == "serve":
        # the router imports need to be after the RefGenConf object is declared
        with rgc as r:
            purge_nonservable(r)
        from .routers import private, version1, version2, version3

        app.include_router(version3.router)
        app.include_router(version1.router, prefix="/v1")
        app.include_router(version2.router, prefix="/v2")
        app.include_router(version3.router, prefix="/v3")
        app.include_router(private.router, prefix=f"/{PRIVATE_API}")
        uvicorn.run(app, host="0.0.0.0", port=args.port)
