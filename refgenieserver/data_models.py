from pydantic import BaseModel
from typing import List, Dict


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
