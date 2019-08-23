import dataclasses
from abc import abstractmethod
from datetime import datetime
from typing import Iterable, Callable, Dict, Tuple

from .ContentStore import ContentStore
from .PageRetriever import PageRetriever
from .utils import PageContent


class PageFilter(PageRetriever):
    def __init__(self, source: ContentStore) -> None:
        super().__init__()
        self.source = source

    def find_recent_changes(self, last_change: datetime) -> Iterable[Tuple[str, datetime]]:
        self.source.refresh()
        yield from ((p.title, p.timestamp) for p in self.source.get_all()
                    if p.timestamp and p.timestamp > last_change)

    def get_titles(self, source: Iterable[str], progress_reporter: Callable[[str], None] = None) \
            -> Iterable[PageContent]:
        for page in self.source.get_multiple(source):
            data, content = self._process_page(page)
            if data is not None:
                yield self.update_content(page, data, content)
            if progress_reporter:
                progress_reporter(page.title)

    def get_all_titles(self,
                       progress_reporter: Callable[[str], None],
                       exclude: Dict[str, datetime] = None,
                       filters=None) -> Iterable[PageContent]:
        for page in self.source.get_all(filters):
            if not exclude or page.title not in exclude or exclude[page.title] < page.timestamp:
                data, content = self._process_page(page)
                if data is not None:
                    yield self.update_content(page, data, content)
            progress_reporter(page.title)

    def update_content(self, page, data, content=None):
        return dataclasses.replace(page, data=data, content=content)

    def _process_page(self, page):
        try:
            res = self.process_page(page)
            return res if res is not None else (None, None)
        except ValueError as err:
            print(f'***** {page.title} *****: {err}')
            return {}, str(err)
        except Exception as err:
            print(f'***** {page.title} *****: {err}')
            raise

    @abstractmethod
    def process_page(self, page: PageContent):
        pass

    def refresh_source(self, progress, reporter):
        if self.source.can_refresh():
            self.source.refresher(progress, reporter, [])

    def can_refresh(self) -> bool:
        return True
