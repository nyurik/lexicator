from dataclasses import dataclass
from typing import Union, Iterable

from pywikiapi import Site

from lexicator import WikidataQueryService


@dataclass
class Config:
    use_bot_limits: bool
    wiktionary: Site
    wikidata: Site
    wdqs: WikidataQueryService
    parse_fields: Union[Iterable[str], None]
