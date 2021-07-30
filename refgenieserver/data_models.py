from platform import version
from typing import Dict, List, Optional

from pydantic import BaseModel


class Tag(BaseModel):
    """
    Tag data model
    """

    asset_path: str
    asset_digest: str
    archive_digest: str
    asset_size: str
    archive_size: str
    seek_keys: Dict[str, str]
    asset_parents: List[str]
    asset_children: List[str]


class Asset(BaseModel):
    """
    Asset data model
    """

    asset_description: str
    tags: Dict[str, Tag]
    default_tag: str


class Genome(BaseModel):
    """
    Genome data model
    """

    genome_description: str
    assets: Dict[str, Asset]
    aliases: List[str]


class AssetClass(BaseModel):
    """
    Asset class data model
    """

    version: str
    name: str
    description: str
    seek_keys: Dict[str, str]
    parents: List[str]


class Recipe(BaseModel):
    """
    Recipe data model
    """

    version: str
    name: str
    description: str
    inputs: Dict[str, Optional[Dict[str, Optional[Dict[str, str]]]]]
    container: str
    command_template_list: List[str]
    custom_properties: Dict[str, str]
    default_tag: str
