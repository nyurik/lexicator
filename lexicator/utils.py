import dataclasses
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, NewType, Tuple, Union, Dict, Any, TypeVar, List

import requests
from mwparserfromhell.nodes import Template
from mwparserfromhell.nodes.extras import Parameter
from pywikiapi import Site, AttrDict
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# template-name, params-dict (or none)
from lexicator import WikidataQueryService

TemplateType = NewType('TemplateType', Tuple[str, Union[Dict[str, str], None]])

T = TypeVar('T')


def to_json(obj, pretty=False):
    if dataclasses.is_dataclass(obj):
        obj = clean_empty_vals(dataclasses.asdict(obj))
    if pretty:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    else:
        return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))


def get_site(host: str) -> Site:
    retries = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
    session = requests.Session()
    session.mount('https://', HTTPAdapter(max_retries=retries))

    return Site(f'https://{host}/w/api.php', session=session, json_object_hook=AttrDict)


def list_to_dict_of_lists(items, key, item_extractor=None):
    result = defaultdict(list)
    for item in items:
        k = key(item)
        if k is not None:
            if item_extractor:
                item = item_extractor(item)
            result[k].append(item)
    return result


def batches(items: Iterable[T], batch_size: int) -> Iterable[List[T]]:
    res = []
    for value in items:
        res.append(value)
        if len(res) >= batch_size:
            yield res
            res = []
    if res:
        yield res


def clean_empty_vals(obj: dict, empty_value=None):
    return {k: v for k, v in obj.items() if v != empty_value}


def trim_timedelta(td: timedelta) -> str:
    return str(td + timedelta(seconds=1)).split('.', 1)[0]


@dataclass(frozen=True)
class PageContent:
    title: str
    timestamp: datetime = None
    ns: int = None
    revid: int = None
    user: str = None
    redirect: str = None
    content: str = None
    data: Any = None

    def to_dict(self):
        obj = clean_empty_vals(dataclasses.asdict(self))
        return obj

    @staticmethod
    def from_dict(obj):
        return PageContent(**obj)


def params_to_wikitext(template):
    return str(Template(template[0], params=[Parameter(k, v) for k, v in template[1].items()]))


@dataclass
class Config:
    use_bot_limits: bool
    wiktionary: Site
    wikidata: Site
    wdqs: WikidataQueryService
    parse_fields: Union[Iterable[str], None]
    print_warnings: bool
