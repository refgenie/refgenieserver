from refgenconf.const import (
    API_ID_ASSET_CLASSES_DICT,
    API_ID_GENOMES_DICT,
    API_ID_RECIPES_DICT,
    CFG_GENOMES_KEY,
    PRIVATE_API,
)
from ..const import PRIV_API_ID
from fastapi import APIRouter

from ..data_models import Dict, Genome
from ..main import _LOGGER, rgc

router = APIRouter()

api_version_tags = [PRIV_API_ID]


@router.get(
    "/genomes/dict",
    tags=api_version_tags,
    operation_id=PRIVATE_API + API_ID_GENOMES_DICT,
    response_model=Dict[str, Genome],
)
async def get_genomes_dict():
    """
    **Private endpoint**, which returns the entire `genomes` section of the config
    """
    _LOGGER.info(f"serving genomes dict: '{rgc[CFG_GENOMES_KEY]}'")
    return rgc[CFG_GENOMES_KEY]


@router.get(
    "/recipes/dict",
    response_model=Dict[str, Dict[str, str]],
    tags=api_version_tags,
    operation_id=PRIVATE_API + API_ID_RECIPES_DICT,
)
async def list_available_recipes():
    """
    **Private endpoint**, which returns the entire `recipes` section of the config
    """
    _LOGGER.info("serving recipes dict")
    return rgc.recipes


@router.get(
    "/asset_classes/dict",
    response_model=Dict[str, Dict[str, str]],
    tags=api_version_tags,
    operation_id=PRIVATE_API + API_ID_ASSET_CLASSES_DICT,
)
async def list_available_asset_classes():
    """
    **Private endpoint**, which returns the entire `asset_classes` section of the config
    """
    _LOGGER.info("serving asset classes dict")
    return rgc.asset_classes
