from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Iterable, Tuple, Union, Callable, Dict, TYPE_CHECKING

from .PageContent import PageContent
from .utils import LogConfig

if TYPE_CHECKING:
    from .ContentStore import ContentStore


class PageRetriever(ABC):
    def __init__(self, log_config: LogConfig = None, source: ContentStore = None, is_remote: bool = False) -> None:
        super().__init__()
        self.log_config = log_config or LogConfig(print_warnings=True, verbose=True)
        self.source: ContentStore = source
        self.is_remote = is_remote

    def init(self):
        pass

    @property
    def follow_redirects(self) -> bool:
        return True

    @abstractmethod
    def find_recent_changes(self, last_change: datetime) -> Iterable[Tuple[str, datetime]]:
        pass

    @abstractmethod
    def get_titles(self,
                   source: Iterable[str],
                   force: Union[bool, str],
                   progress_reporter: Callable[[str], None] = None) \
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

    def custom_refresh(self, filters=None) -> Iterable[str]:
        pass

    def before_refresh(self, filters=None):
        pass

    def after_refresh(self, filters=None):
        pass
