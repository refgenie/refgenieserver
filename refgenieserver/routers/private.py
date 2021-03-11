from ..const import *
from ..main import rgc, templates, _LOGGER, app
from ..data_models import Genome, Dict
from fastapi import APIRouter

router = APIRouter()


@router.get(
    "/genomes/dict",
    operation_id=PRIVATE_API + API_ID_GENOMES_DICT,
    response_model=Dict[str, Genome],
    include_in_schema=False,
)
async def get_genomes_dict():
    """
    **Private endpoint!**, which returns the entire 'genomes' part of the config
    """
    _LOGGER.info(f"serving genomes dict: '{rgc[CFG_GENOMES_KEY]}'")
    return rgc[CFG_GENOMES_KEY]
