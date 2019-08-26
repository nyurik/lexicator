import dataclasses
import json
import re
from datetime import datetime
from html import unescape
from itertools import chain
from typing import Iterable, Union, Callable, Dict, Tuple

from pywikiapi import Site
from pywikiapi.utils import to_datetime

from .WikidataQueryService import entity_id, WikidataQueryService
from .Properties import Q_PART_OF_SPEECH, Q_RUSSIAN_LANG
from .PageRetriever import PageRetriever
from .consts import NS_MAIN, NS_TEMPLATE, re_template_names, NS_LEXEME
from .utils import PageContent, to_json, batches, Config
from pywikiapi import to_timestamp


class WikipageDownloader(PageRetriever):
    def __init__(self, config: Config, site: Site, namespace: int, follow_redirects: bool = True,
                 title_filter: Callable[[int, str], bool] = None):
        super().__init__(config, is_remote=True)
        self.site = site
        self.namespace = namespace
        self._follow_redirects = follow_redirects
        self.title_filter = title_filter or (lambda n, t: True)

        self.download_titles_query = dict(
            prop=['revisions', 'info'],
            rvprop=['content', 'ids', 'timestamp', 'user'],
            rvslots='main',
        )

        self.find_recent_changes_query = dict(
            list='recentchanges',
            rcdir='newer',
            rcprop=['title', 'timestamp'],
            rclimit='max',
            rcnamespace=namespace)
        if self.follow_redirects:
            self.find_recent_changes_query['rcshow'] = '!redirect'

    @property
    def follow_redirects(self) -> bool:
        return self._follow_redirects

    def find_recent_changes(self, last_change: datetime) -> Iterable[Tuple[str, datetime]]:
        result: Dict[str, datetime] = {}
        if self.site:
            print(f"API: query recent changes since {last_change}")
            for res in self.site.query(**self.find_recent_changes_query, rcstart=last_change):
                for ch in res.recentchanges:
                    if not self.title_filter(ch.ns, ch.title):
                        continue
                    result[ch.title] = to_datetime(ch.timestamp)
        yield from result.items()

    def get_titles(self,
                   source: Iterable[str],
                   force: Union[bool, str],
                   progress_reporter: Callable[[str], None] = None) -> Iterable[PageContent]:
        if not self.site:
            return []
        for batch in batches(source, 50):
            print(f"API: query {len(batch)} titles: [{', '.join(batch[:3])}{', ...' if len(batch) > 3 else ''}]")
            for query in self.site.query(**self.download_titles_query, titles=batch, redirects=self.follow_redirects):
                if 'pages' in query:
                    for page in query.pages:
                        if 'missing' not in page:
                            val = self.to_content(page)
                            if val:
                                yield val
                        if progress_reporter:
                            progress_reporter(page.title)
                redirects = []
                if 'normalized' in query:
                    redirects.append(query.normalized)
                if 'redirects' in query:
                    redirects.append(query.redirects)
                if redirects:
                    yield from (PageContent(title=r['from'], redirect=r['to']) for r in chain.from_iterable(redirects))

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
                if not exclude or (v not in exclude or exclude[v.title] < v.timestamp):
                    yield v

        yield from self.get_titles(get_tiles(), force=False, progress_reporter=progress_reporter)

    def can_refresh(self) -> bool:
        return bool(self.site)


class DownloaderForWords(WikipageDownloader):

    def __init__(self, config: Config):
        super().__init__(config, config.wiktionary, NS_MAIN)

    def get_all_titles(self, progress_reporter: Callable[[str], None],
                       exclude: Dict[str, datetime] = None,
                       filters=None) -> Iterable[PageContent]:
        if filters and len(filters) > 0:
            raise ValueError('Filters not supported')

        if len(exclude) < 100:
            if self.site:
                print(f"API: query all content from allpages generator from namespace {self.namespace}")
                pages_with_content = dict(**self.download_titles_query, generator='allpages',
                                          gapnamespace=self.namespace,
                                          gaplimit='50', gapfilterredir='nonredirects')
                for page in self.site.query_pages(**pages_with_content):
                    val = self.to_content(page)
                    if val.title and (not exclude or (val.title not in exclude or exclude[val.title] < val.timestamp)):
                        yield val
                    progress_reporter(val.title)
        else:
            yield from super().get_all_titles(progress_reporter, exclude, filters)


class DownloaderForTemplates(WikipageDownloader):
    def __init__(self, config: Config):
        super().__init__(config, config.wiktionary, NS_TEMPLATE, title_filter=self.title_filter)

        # noinspection SpellCheckingInspection
        self.re_html_comment = re.compile(r'<!--[\s\S]*?-->')
        self.re_noinclude = re.compile(r'<\s*noinclude\s*>([^<]*)<\s*/\s*noinclude\s*>')
        self.re_includeonly = re.compile(r'<\s*includeonly\s*>([^<]*)<\s*/\s*includeonly\s*>')

    def to_content(self, page) -> Union[PageContent, None]:
        p = super().to_content(page)
        if p:
            text = p.content
            text = self.re_html_comment.sub('', text)
            text = self.re_noinclude.sub('', text)
            text = self.re_includeonly.sub(r'\1', text)
            text = unescape(text)
            return dataclasses.replace(p, content=text)

    # noinspection PyUnusedLocal
    @staticmethod
    def title_filter(ns: int, title: str):
        return re_template_names.match(title) or title


class LexemDownloader(WikipageDownloader):
    def __init__(self, config: Config):
        super().__init__(config, config.wikidata, NS_LEXEME)
        self.wdqs = config.wdqs

    def query_wdqs(self, last_change: datetime = None, get_lemma=False):
        if not self.wdqs:
            print(f"API: WDQS is disabled")
            return {}

        if last_change:
            print(f"API: querying WDQS for lexemes modified after {last_change}")
        else:
            print(f"API: querying WDQS for all lexemes")

        categories = {Q_PART_OF_SPEECH['noun']}

        # from datetime import timedelta
        # last_change -= timedelta(days=5)
        #
        res = self.wdqs.query(f"""\
SELECT ?lexemeId{' ?lemma' if get_lemma else ''} ?ts WHERE {{
  VALUES ?category {{ {' '.join(['wd:' + c for c in categories])} }}
  ?lexemeId <http://purl.org/dc/terms/language> wd:{Q_RUSSIAN_LANG};
      {'wikibase:lemma ?lemma;' if get_lemma else ''}
      wikibase:lexicalCategory ?category;
      schema:dateModified ?ts.
  {f'FILTER (?ts >= "{to_timestamp(last_change)}"^^xsd:dateTime)' if last_change else ''}
}}""")
        if get_lemma:
            return {'Lexeme:' + entity_id(r['lexemeId']): (r['lemma']['value'], r['ts']['value']) for r in res}
        elif last_change:
            return (('Lexeme:' + entity_id(r['lexemeId']), to_datetime(r['ts']['value'])) for r in res)
        else:
            return ('Lexeme:' + entity_id(r['lexemeId']) for r in res)

    def find_titles(self) -> Iterable[str]:
        yield from self.query_wdqs()

    def find_recent_changes(self, last_change: datetime) -> Iterable[Tuple[str, datetime]]:
        yield from self.query_wdqs(last_change)

    def to_content(self, page) -> Union[PageContent, None]:
        p = super().to_content(page)
        if p:
            data = json.loads(p.content)
            p = dataclasses.replace(
                p, data=data['lemmas']['ru']['value'], content=to_json(data))
        return p

    # def get_existing_lexemes(self) -> Dict[str, Dict[str, List]]:
    #     if not self.lexemes or not self.lexical_categories:
    #         return {}
    #     category_ids = self.lexical_categories.ids()
    #     # list of lexemes per grammatical category
    #     entities = list_to_dict_of_lists(
    #         (l for l in self.lexemes.get() if 'ru' in l.lemmas and l.lexicalCategory in category_ids),
    #         lambda l: category_ids[l.lexicalCategory]
    #     )
    #     count = sum((len(v) for v in entities.values()))
    #     if count != len(self.lexemes.get()):
    #         print(f'{len(self.lexemes.get()) - count} entities have not been recognized')
    #     # convert all lists into lemma -> list, where most lists will just have one element
    #     return {
    #         k: list_to_dict_of_lists(v, lambda l: l.lemmas.ru.value)
    #         for k, v in entities.items()
    #     }
    #
