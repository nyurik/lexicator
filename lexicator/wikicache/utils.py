import dataclasses
import json
from datetime import timedelta
from typing import Iterable, List, TypeVar

from pywikiapi import Site

T = TypeVar('T')


def clean_empty_vals(obj: dict, empty_value=None):
    return {k: v for k, v in obj.items() if v != empty_value}


def batches(items: Iterable[T], batch_size: int) -> Iterable[List[T]]:
    res = []
    for value in items:
        res.append(value)
        if len(res) >= batch_size:
            yield res
            res = []
    if res:
        yield res


def trim_timedelta(td: timedelta) -> str:
    return str(td + timedelta(seconds=1)).split('.', 1)[0]


def to_json(obj, pretty=False):
    if dataclasses.is_dataclass(obj):
        obj = clean_empty_vals(dataclasses.asdict(obj))
    if pretty:
        return json.dumps(obj, ensure_ascii=False, indent=2)
    else:
        return json.dumps(obj, ensure_ascii=False, separators=(',', ':'))


def json_key(template, params):
    return json.dumps({template: params}, ensure_ascii=False, separators=(',', ':'), sort_keys=True)


@dataclasses.dataclass
class LogConfig:
    print_warnings: bool = True
    verbose: bool = False


class MwSite(Site):
    def __init__(self, url, lang_code: str, *args, **kwargs):
        super().__init__(url, *args, **kwargs)
        self.lang_code = lang_code
        self._use_bot_limits = None

    @property
    def use_bot_limits(self) -> bool:
        return self.is_bot()
