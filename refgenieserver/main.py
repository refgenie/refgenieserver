from .const import *
from .helpers import build_parser
from .server_builder import archive
from refgenconf import RefGenConf, select_genome_config
from fastapi import FastAPI
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates
import logmuse
import sys
import uvicorn

app = FastAPI()
app.mount("/" + STATIC_DIRNAME, StaticFiles(directory=STATIC_PATH), name=STATIC_DIRNAME)
templates = Jinja2Templates(directory=TEMPLATES_PATH)

global rgc, _LOGGER


def main():
    global rgc, _LOGGER
    parser = build_parser()
    args = parser.parse_args()
    logger_args = dict(name=PKG_NAME, fmt=LOG_FORMAT, level=5) if args.debug else dict(name=PKG_NAME, fmt=LOG_FORMAT)
    _LOGGER = logmuse.setup_logger(**logger_args)
    rgc = RefGenConf(select_genome_config(args.config))
    # the router imports need to be after the RefGenConf object is declared
    from .routers import version1, version2
    app.include_router(version1.router)
    app.include_router(
        version2.router,
        prefix="/v2",
    )
    assert len(rgc) > 0, "You must provide a config file or set the '{}' environment variable".\
        format(", ".join(CFG_ENV_VARS))
    if args.command == "archive":
        archive(rgc, args)
    elif args.command == "serve":
        _LOGGER.info("serving")
        uvicorn.run(app, host="0.0.0.0", port=args.port)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        _LOGGER.info("Program canceled by user")
        sys.exit(1)

