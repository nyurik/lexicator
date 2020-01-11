import dataclasses
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from .utils import clean_empty_vals, to_compact_json


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

    def is_deleted(self):
        return self.content is None and self.data is None and self.timestamp is None and self.redirect is None

    def __str__(self):
        msg = f"title={self.title}  ts={self.timestamp.isoformat()}  ns={self.ns} revid={self.revid} "
        msg += f"user={self.user} redirect={self.redirect}"
        if self.content and len(self.content) > 30:
            if not self.data:
                msg += f" data={self.data}"
            msg += f"\ncontent={self.content}\n"
        else:
            msg += f" content={self.content}"
            if not self.data:
                msg += f" data={self.data}"
        if self.data:
            if isinstance(self.data, list):
                lines = []
                for line in self.data:
                    if isinstance(line, tuple) or isinstance(line, list):
                        lines.append(', '.join((to_compact_json(v) for v in line)))
                    else:
                        lines.append(str(line))
                joiner = '\n     '
                msg += f"\ndata={joiner.join(lines)}"
            else:
                msg += f"\ndata={self.data}"
        return msg
