from datetime import datetime
from typing import Callable, Dict, Iterable

from lexicator.consts import NS_MAIN
from .PageContent import PageContent
from .WikipageDownloader import WikipageDownloader
from .utils import LogConfig, MwSite


class WiktionaryWordDownloader(WikipageDownloader):
    def __init__(self, wiktionary: MwSite, log_config: LogConfig):
        super().__init__(site=wiktionary, namespace=NS_MAIN, log_config=log_config)

    def get_all_titles(self, progress_reporter: Callable[[str], None],
                       exclude: Dict[str, datetime] = None,
                       filters=None) -> Iterable[PageContent]:
        if filters and len(filters) > 0:
            raise ValueError('Filters not supported')

        if len(exclude) < 100:
            if self.site:
                print(f"API: query all content from allpages generator from namespace {self.namespace}")
                pages_with_content = dict(**self.download_titles_query,
                                          generator='allpages',
                                          gapnamespace=self.namespace,
                                          gaplimit=200 if self.site.use_bot_limits else 50,
                                          gapfilterredir='nonredirects')
                for page in self.site.query_pages(**pages_with_content):
                    val = self.to_content(page)
                    if val.title and (not exclude or (val.title not in exclude or exclude[val.title] < val.timestamp)):
                        yield val
                    progress_reporter(val.title)
        else:
            yield from super().get_all_titles(progress_reporter, exclude, filters)
