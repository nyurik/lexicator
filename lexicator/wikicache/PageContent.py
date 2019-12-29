import dataclasses
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from lexicator.wikicache.utils import clean_empty_vals


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

    # @staticmethod
    # def from_dict(obj):
    #     return PageContent(**obj)

    def is_deleted(self):
        return self.content is None and self.data is None and self.timestamp is None and self.redirect is None
