import dataclasses
from abc import abstractmethod
from datetime import datetime
from typing import Iterable, Callable, Dict, Tuple, Union

from .PageRetriever import PageRetriever
from .utils import PageContent


def update_content(page, data, content=None):
    return dataclasses.replace(page, data=data, content=content)


class PageFilter(PageRetriever):
    def find_recent_changes(self, last_change: datetime) -> Iterable[Tuple[str, datetime]]:
        self.source.refresh()
        yield from ((p.title, p.timestamp) for p in self.source.get_all()
                    if p.timestamp and p.timestamp > last_change)

    def get_titles(self,
                   source: Iterable[str],
                   force: Union[bool, str],
                   progress_reporter: Callable[[str], None] = None) -> Iterable[PageContent]:
        for page in self.source.get_multiple(source, force):
            data, content = self._process_page(page, force)
            if data is not None:
                yield update_content(page, data, content)
            if progress_reporter:
                progress_reporter(page.title)

    def get_all_titles(self,
                       progress_reporter: Callable[[str], None],
                       exclude: Dict[str, datetime] = None,
                       filters=None,
                       force: Union[bool, str] = None) -> Iterable[PageContent]:
        for page in self.source.get_all(filters):
            if not exclude or page.title not in exclude or exclude[page.title] < page.timestamp:
                data, content = self._process_page(page, force)
                if data is not None and content is not None:
                    yield update_content(page, data, content)
            progress_reporter(page.title)

    def _process_page(self, page: PageContent, force: Union[bool, str]):
        try:
            res = self.process_page(page, force)
            return res if res is not None else (None, None)
        except ValueError as err:
            if self.config.print_warnings:
                print(f'***** {page.title} *****: {err}')
            return None, str(err)
        except KeyError as err:
            if self.config.print_warnings:
                print(f'***** {page.title} *****: Key not found: {err}')
            return None, str(err)
        except Exception as err:
            print(f'***** {page.title} *****: {err}')
            raise

    @abstractmethod
    def process_page(self, page: PageContent, force: Union[bool, str]):
        pass

    def refresh_source(self, progress, reporter):
        if self.source.can_refresh():
            self.source.refresher(progress, reporter, [])

    def can_refresh(self) -> bool:
        return True
