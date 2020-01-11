from pathlib import Path
from typing import Union

import requests
from pywikiapi import AttrDict
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from lexicator.wikicache import WikidataQueryService, LogConfig, MwSite


class Config(LogConfig):
    wiktionary: MwSite
    wikidata: MwSite
    wdqs: WikidataQueryService

    def __init__(self,
                 lang_code: str,
                 user: str,
                 password: Union[Path, str],
                 print_warnings: bool = True,
                 verbose: bool = False,
                 ) -> None:
        super().__init__()
        self.print_warnings = print_warnings
        self.verbose = verbose
        self.wiktionary = get_site(f'{lang_code}.wiktionary.org', user, password)
        self.wikidata = get_site('www.wikidata.org', user, password)
        self.wdqs = WikidataQueryService()


def get_site(host: str, username: str, password: Union[Path, str], max_lag: int = 5) -> MwSite:
    retries = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
    session = requests.Session()
    session.mount('https://', HTTPAdapter(max_retries=retries))

    lang_code = host.split('.')[0] if '.wiktionary.' in host else None
    site = MwSite(f'https://{host}/w/api.php',
                  lang_code=lang_code,
                  session=session,
                  json_object_hook=AttrDict)

    if isinstance(password, Path):
        password = password.read_text().strip()
    site.login(username, password=password, on_demand=True)
    site.maxlag = max_lag

    return site
