from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterable, Callable, Dict, Tuple, Any

from .utils import PageContent


class PageRetriever(ABC):
    source: 'ContentStore' = None

    def init(self):
        pass

    @property
    def follow_redirects(self) -> bool:
        return True

    @abstractmethod
    def find_recent_changes(self, last_change: datetime) -> Iterable[Tuple[str, datetime]]:
        pass

    @abstractmethod
    def get_titles(self, source: Iterable[str], progress_reporter: Callable[[str], None] = None) \
            -> Iterable[PageContent]:
        pass

    @abstractmethod
    def get_all_titles(self, progress_reporter: Callable[[str], None],
                       exclude: Dict[str, datetime] = None,
                       filters=None) \
            -> Iterable[PageContent]:
        pass

    def refresh_source(self, progress, reporter):
        pass

    @abstractmethod
    def can_refresh(self) -> bool:
        pass

    def custom_refresh(self, *filters) -> Iterable[str]:
        pass
