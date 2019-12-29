from collections import defaultdict
from dataclasses import dataclass
from typing import NewType, Tuple, Union, Dict, TypeVar

import requests
import unicodedata
from pywikiapi import Site, AttrDict
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# template-name, params-dict (or none)
from lexicator.wikicache import WikidataQueryService
from lexicator.consts import STRESS_SYMBOL_PRI, STRESS_SYMBOL_SEC
from lexicator.wikicache.utils import LogConfig, MwSite

TemplateType = NewType('TemplateType', Tuple[str, Union[Dict[str, str], None]])

T = TypeVar('T')


def get_site(host: str, use_bot_limits: bool) -> MwSite:
    retries = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
    session = requests.Session()
    session.mount('https://', HTTPAdapter(max_retries=retries))

    site = MwSite(f'https://{host}/w/api.php', use_bot_limits=use_bot_limits, session=session,
                  json_object_hook=AttrDict)
    site.auto_post_min_size = 1500

    return site


def list_to_dict_of_lists(items, key, item_extractor=None):
    result = defaultdict(list)
    for item in items:
        k = key(item)
        if k is not None:
            if item_extractor:
                item = item_extractor(item)
            result[k].append(item)
    return result


def remove_stress(word):
    return unicodedata.normalize(
        'NFC', unicodedata.normalize('NFD', word).replace(STRESS_SYMBOL_PRI, '').replace(STRESS_SYMBOL_SEC, ''))


@dataclass
class Config(LogConfig):
    lang_code: str
    wiktionary: MwSite
    wikidata: MwSite
    wdqs: WikidataQueryService
