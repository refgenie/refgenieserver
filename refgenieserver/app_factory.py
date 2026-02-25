"""Factory function to create a configured refgenieserver FastAPI app."""

from __future__ import annotations

import logging
import sys

from fastapi import FastAPI
from refgenconf import RefGenConf

from .const import PKG_NAME, PRIVATE_API, TAGS_METADATA
from .helpers import purge_nonservable

_LOGGER = logging.getLogger(PKG_NAME)


def create_app(config_path: str, archive_base_dir: str | None = None) -> FastAPI:
    """Create a configured FastAPI app for refgenieserver.

    This builds a fresh FastAPI app with the real refgenieserver routers,
    configured from a given YAML config file. Used both for production
    (as an alternative to the CLI entry point) and for integration tests.

    Args:
        config_path: Path to the refgenie server config YAML.
        archive_base_dir: Override for BASE_DIR (default: /genomes).
            Used in tests to point at a temp directory.

    Returns:
        Configured FastAPI app ready to serve.
    """
    # Use sys.modules to get the actual module objects. Using
    # `import refgenieserver.main as m` can return a different object
    # than what's in sys.modules (due to __init__.py's `from .main import *`),
    # which means attribute modifications won't be visible to other modules.
    import refgenieserver.const  # noqa: F401 ensure loaded
    import refgenieserver.helpers  # noqa: F401 ensure loaded
    import refgenieserver.main  # noqa: F401 ensure loaded

    main_module = sys.modules["refgenieserver.main"]
    const_module = sys.modules["refgenieserver.const"]
    helpers_module = sys.modules["refgenieserver.helpers"]

    # Load config and purge non-servable entries
    rgc = RefGenConf.from_yaml_file(config_path)
    purge_nonservable(rgc)

    # Override the module-level globals that the routers import.
    # The routers do `from ..main import _LOGGER, rgc, app, templates`
    # which reads from main's module dict at import time.
    main_module.rgc = rgc
    main_module._LOGGER = _LOGGER

    if archive_base_dir is not None:
        # Must override BASE_DIR in both const and helpers modules,
        # because helpers.py uses `from .const import *` which copies
        # BASE_DIR into helpers' own namespace.
        const_module.BASE_DIR = archive_base_dir
        helpers_module.BASE_DIR = archive_base_dir

    from ._version import __version__ as server_v

    app = FastAPI(
        title=PKG_NAME,
        description="a web interface and RESTful API for reference genome assets",
        version=server_v,
        openapi_tags=TAGS_METADATA,
    )

    # Set the app on main_module so routers that import `app` from main
    # can access it (needed for openapi spec introspection)
    main_module.app = app

    # Import routers AFTER rgc is set (they read rgc at import time)
    from .routers import private, version3

    app.include_router(version3.router)
    app.include_router(version3.router, prefix="/v3")
    app.include_router(private.router, prefix=f"/{PRIVATE_API}")

    return app
