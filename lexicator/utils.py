from dataclasses import dataclass

import requests
from pywikiapi import AttrDict
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from lexicator.wikicache import WikidataQueryService, LogConfig, MwSite


@dataclass
class Config(LogConfig):
    wiktionary: MwSite
    wikidata: MwSite
    wdqs: WikidataQueryService


def get_site(host: str, use_bot_limits: bool) -> MwSite:
    retries = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
    session = requests.Session()
    session.mount('https://', HTTPAdapter(max_retries=retries))

    lang_code = host.split('.')[0] if '.wiktionary.' in host else None
    site = MwSite(f'https://{host}/w/api.php',
                  lang_code=lang_code,
                  use_bot_limits=use_bot_limits,
                  session=session,
                  json_object_hook=AttrDict)
    site.auto_post_min_size = 1500

    return site
