import dataclasses
import json
from collections import defaultdict
from typing import Iterable, NewType, Tuple, Union, Dict, Iterator

import requests
from pywikiapi import Site, AttrDict
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from .consts import re_template_names, re_template_name_suspect

# template-name, params-dict (or none)
TemplateType = NewType('TemplateType', Tuple[str, Union[Dict[str, str], None]])


def to_json(obj, pretty=False):
    if dataclasses.is_dataclass(obj):
        obj = {k: v for k, v in dataclasses.asdict(obj).items() if v is not None}
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
            if item_extractor: item = item_extractor(item)
            result[k].append(item)
    return result


def lang_pick(vals, lang):
    return vals[lang] if lang in vals else vals['en']


def batches(items: Iterable, batch_size: int):
    res = []
    for value in items:
        res.append(value)
        if len(res) >= batch_size:
            yield res
            res = []
    if res:
        yield res


def extract_template_params(code) -> Iterator[TemplateType]:
    for param in code.filter_templates():
        template = str(param.name).strip()
        if re_template_names.match(template):
            yield template, {str(p.name).strip(): str(p.value).strip() for p in param.params}
        elif re_template_name_suspect.match(template):
            yield template, None
