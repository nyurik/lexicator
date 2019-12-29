from datetime import datetime
from typing import Callable, Iterable, Tuple, Dict, Union

from pywikiapi import to_datetime

from lexicator.wikicache.PageContent import PageContent
from lexicator.wikicache.PageRetriever import PageRetriever
from lexicator.wikicache.utils import trim_timedelta, batches, to_json, LogConfig, MwSite


class WikipageDownloader(PageRetriever):
    def __init__(self,
                 site: MwSite,
                 namespace: int,
                 follow_redirects: bool = True,
                 store_redirects: bool = False,
                 title_filter: Callable[[int, str], bool] = None,
                 log_config: LogConfig = None):
        super().__init__(log_config=log_config, is_remote=True)
        self.site = site
        self.namespace = namespace
        self._follow_redirects = follow_redirects
        self.store_redirects = store_redirects
        self.title_filter = title_filter or (lambda n, t: True)

        self.download_titles_query = dict(
            prop=['revisions', 'info'],
            rvprop=['content', 'ids', 'timestamp', 'user'],
            rvslots='main',
        )

        self.find_recent_changes_query = dict(
            list='recentchanges',
            rcdir='newer',
            rctype=['edit', 'new', 'log'],
            rcprop=['title', 'timestamp', 'loginfo'],
            rclimit='max',
            rcnamespace=namespace)

    @property
    def follow_redirects(self) -> bool:
        return self._follow_redirects

    def find_recent_changes(self, last_change: datetime) -> Iterable[Tuple[str, datetime]]:
        result: Dict[str, datetime] = {}
        if self.site:
            since = trim_timedelta(datetime.utcnow() - last_change)
            print(f"API: query recent changes since in the last {since} (since {last_change})")
            for res in self.site.query(**self.find_recent_changes_query, rcstart=last_change):
                for ch in res.recentchanges:
                    if 'title' not in ch or not self.title_filter(ch.ns, ch.title):
                        continue
                    if not self.recent_changes_filter(ch):
                        continue
                    result[ch.title] = to_datetime(ch.timestamp)
        yield from result.items()

    def get_titles(self,
                   source: Iterable[str],
                   force: Union[bool, str],
                   progress_reporter: Callable[[str], None] = None) -> Iterable[PageContent]:
        if not self.site:
            return []
        for batch in batches(source, 250 if self.site.use_bot_limits else 50):
            print(f"API: query {len(batch)} titles: [{', '.join(batch[:3])}{', ...' if len(batch) > 3 else ''}]")
            for query in self.site.query(**self.download_titles_query, titles=batch, redirects=self.follow_redirects):
                if 'pages' in query:
                    for page in query.pages:
                        # Links to other namespaces are treated as deleted
                        if 'missing' not in page and page.ns == self.namespace:
                            val = self.to_content(page)
                            if val:
                                yield val
                        else:
                            yield PageContent(title=page.title)  # delete it
                        if progress_reporter:
                            progress_reporter(page.title)

                if self.store_redirects:
                    def to_page(row):
                        return PageContent(title=row['from'], redirect=row['to'])
                else:
                    def to_page(row):
                        return PageContent(title=row['from'])  # mark page for deletion

                if 'normalized' in query:
                    yield from (to_page(r) for r in query.normalized)
                if 'redirects' in query:
                    yield from (to_page(r) for r in query.redirects)

    def to_content(self, page) -> Union[PageContent, None]:
        try:
            if len(page.revisions) != 1:
                raise ValueError(f'revision count is unexpected')
            rev = page.revisions[0]
            content = rev.slots.main.content
            return PageContent(title=page.title, ns=page.ns, content=content,
                               timestamp=to_datetime(rev.timestamp), revid=rev.revid, user=rev.user)
        except Exception as err:
            print(f"Page {page} has no useful content in {to_json(page)}: {err}")
            return None

    def find_titles(self) -> Iterable[str]:
        titles = set()
        if self.site:
            print(f"API: querying allpages for namespace {self.namespace}")
            for q in self.site.query(list='allpages', apnamespace=self.namespace, aplimit='max'):
                for p in q['allpages']:
                    if p.title in titles or not self.title_filter(p.ns, p.title):
                        continue
                    titles.add(p.title)
                    yield p.title

    def get_all_titles(self, progress_reporter: Callable[[str], None],
                       exclude: Dict[str, datetime] = None,
                       filters=None) -> Iterable[PageContent]:
        if filters and len(filters) > 0:
            raise ValueError('Filters not supported')

        def get_tiles():
            for v in self.find_titles():
                if not exclude or v not in exclude:
                    yield v

        yield from self.get_titles(get_tiles(), force=False, progress_reporter=progress_reporter)

    def can_refresh(self) -> bool:
        return bool(self.site)

    def recent_changes_filter(self, rc):
        return True
