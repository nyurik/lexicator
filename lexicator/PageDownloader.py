import dataclasses
import json
import re
from datetime import datetime, timedelta
from html import unescape
from typing import Iterable, Union, Callable, Dict, Tuple

from pywikiapi import Site
from pywikiapi import to_timestamp
from pywikiapi.utils import to_datetime

from lexicator.PageRetriever import PageRetriever
from lexicator.Properties import Q_RUSSIAN_LANG
from lexicator.WikidataQueryService import entity_id
from lexicator.consts import NS_MAIN, NS_TEMPLATE, re_template_names, NS_LEXEME
from lexicator.utils import PageContent, to_json, batches, Config, trim_timedelta


class WikipageDownloader(PageRetriever):
    def __init__(self,
                 config: Config,
                 site: Site,
                 namespace: int,
                 follow_redirects: bool = True,
                 store_redirects: bool = False,
                 title_filter: Callable[[int, str], bool] = None):
        super().__init__(config, is_remote=True)
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
        for batch in batches(source, 250 if self.config.use_bot_limits else 50):
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


class DownloaderForWords(WikipageDownloader):

    def __init__(self, config: Config):
        super().__init__(config, site=config.wiktionary, namespace=NS_MAIN)

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
                                          gaplimit=200 if self.config.use_bot_limits else 50,
                                          gapfilterredir='nonredirects')
                for page in self.site.query_pages(**pages_with_content):
                    val = self.to_content(page)
                    if val.title and (not exclude or (val.title not in exclude or exclude[val.title] < val.timestamp)):
                        yield val
                    progress_reporter(val.title)
        else:
            yield from super().get_all_titles(progress_reporter, exclude, filters)


class DownloaderForTemplates(WikipageDownloader):
    def __init__(self, config: Config):
        super().__init__(config, site=config.wiktionary, namespace=NS_TEMPLATE, title_filter=self.title_filter,
                         store_redirects=True)

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


class LexemeDownloader(WikipageDownloader):
    def __init__(self, config: Config):
        super().__init__(config, site=config.wikidata, namespace=NS_LEXEME)
        self.find_recent_changes_query['rctype'] = 'log'  # only look at the log entries
        self.wdqs = config.wdqs

    def query_wdqs(self, last_change: datetime = None, get_lemma=False, thorough=False):
        # Use thorough for recursive check of all redirects - slower

        if not self.wdqs:
            print(f"API: WDQS is disabled")
            return {}

        if last_change:
            since = trim_timedelta(datetime.utcnow() - last_change)
            print(f"API: querying WDQS for lexemes in the last {since} (since {last_change})")
        else:
            print(f"API: querying WDQS for all lexemes")

        # from datetime import timedelta
        # last_change -= timedelta(days=5)
        #
        if get_lemma:
            query = f"""\
SELECT ?lexemeId ?lemma ?ts WHERE {{
  ?lexemeId <http://purl.org/dc/terms/language> wd:{Q_RUSSIAN_LANG};
    wikibase:lemma ?lemma;
    schema:dateModified ?ts.
  {f'FILTER (?ts >= "{to_timestamp(last_change)}"^^xsd:dateTime)' if last_change else ''}
}}"""
        else:
            query = f"""\
SELECT ?lexemeId ?ts WHERE {{
{{
  ?lexemeId <http://purl.org/dc/terms/language> wd:{Q_RUSSIAN_LANG};
    schema:dateModified ?ts.
}} UNION {{
  ?lexemeId owl:sameAs{'+' if thorough else ''} / <http://purl.org/dc/terms/language> wd:{Q_RUSSIAN_LANG};
    schema:dateModified ?ts.
}}
  {f'FILTER (?ts >= "{to_timestamp(last_change)}"^^xsd:dateTime)' if last_change else ''}
}}"""

        res = self.wdqs.query(query)
        if get_lemma:
            return {'Lexeme:' + entity_id(r['lexemeId']): (r['lemma']['value'], r['ts']['value']) for r in res}
        elif last_change:
            return (('Lexeme:' + entity_id(r['lexemeId']), to_datetime(r['ts']['value'])) for r in res)
        else:
            return ('Lexeme:' + entity_id(r['lexemeId']) for r in res)

    def find_titles(self) -> Iterable[str]:
        yield from self.query_wdqs()

    def find_recent_changes(self, last_change: datetime) -> Iterable[Tuple[str, datetime]]:
        # detect deleted lexemes using RC log, modified and redirected using wdqs
        results = {}
        for word, ts in super(LexemeDownloader, self).find_recent_changes(last_change):
            if word not in results or results[word] < ts:
                results[word] = ts
        # WDQS might be a few minutes behind
        for word, ts in self.query_wdqs(last_change - timedelta(minutes=3)):
            if word not in results or results[word] < ts:
                results[word] = ts
        yield from results.items()

    def recent_changes_filter(self, rc):
        return rc.type == 'log' and rc.logaction == 'delete'

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
