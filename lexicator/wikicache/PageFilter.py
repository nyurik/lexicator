import dataclasses
from abc import abstractmethod
from datetime import datetime
from typing import Iterable, Callable, Dict, Tuple, Union

from .PageContent import PageContent
from .PageRetriever import PageRetriever


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
        yield from self._iterate(self.source.get_multiple(source, force), force, progress_reporter)

    def get_all_titles(self,
                       progress_reporter: Callable[[str], None],
                       exclude: Dict[str, datetime] = None,
                       filters=None,
                       force: Union[bool, str] = None) -> Iterable[PageContent]:
        yield from self._iterate((
            page for page in self.source.get_all(filters=filters)
            if not exclude or page.title not in exclude or exclude[page.title] < page.timestamp
        ), force, progress_reporter)

    def _iterate(self, source, force, progress_reporter):
        for page in source:
            try:
                res = self.process_page(page, force)
                if res:
                    yield res
            except (ValueError, KeyError) as err:
                if self.log_config.print_warnings:
                    print(f"***** {page.title} ***** {'key not found' if isinstance(err, KeyError) else ''}: {err}")
                    # raise
                yield update_content(page, None, str(err))
            except Exception as err:
                print(f'***** {page.title} *****: {err}')
                raise
            if progress_reporter:
                progress_reporter(page.title)

    @abstractmethod
    def process_page(self, page: PageContent, force: Union[bool, str]) -> Union[PageContent, None]:
        pass

    def refresh_source(self, progress, reporter):
        if self.source.can_refresh():
            self.source.refresher(progress, reporter, [])

    def can_refresh(self) -> bool:
        return True
