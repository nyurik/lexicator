import dataclasses
import json
from datetime import datetime, timedelta
from typing import Iterable, Tuple, Union

from pywikiapi import to_timestamp, to_datetime

from lexicator.consts import Q_LANGUAGE_CODES
from lexicator.wikicache import WikidataQueryService
from lexicator.wikicache.PageContent import PageContent
from lexicator.wikicache.WikidataQueryService import entity_id
from lexicator.wikicache.WikipageDownloader import WikipageDownloader
from lexicator.wikicache.consts import NS_LEXEME
from lexicator.wikicache.utils import trim_timedelta, to_json, LogConfig, MwSite


class LexemeDownloader(WikipageDownloader):
    def __init__(self, wikidata_site: MwSite, wdqs_site: WikidataQueryService,
                 lang_code: str, log_config: LogConfig):
        super().__init__(site=wikidata_site, namespace=NS_LEXEME, log_config=log_config)
        self.lang_code = lang_code
        self.find_recent_changes_query['rctype'] = 'log'  # only look at the log entries
        self.wdqs = wdqs_site
        self.q_language = Q_LANGUAGE_CODES[lang_code]

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
  ?lexemeId <http://purl.org/dc/terms/language> wd:{self.q_language};
    wikibase:lemma ?lemma;
    schema:dateModified ?ts.
  {f'FILTER (?ts >= "{to_timestamp(last_change)}"^^xsd:dateTime)' if last_change else ''}
}}"""
        else:
            query = f"""\
SELECT ?lexemeId ?ts WHERE {{
{{
  ?lexemeId <http://purl.org/dc/terms/language> wd:{self.q_language};
    schema:dateModified ?ts.
}} UNION {{
  ?lexemeId owl:sameAs{'+' if thorough else ''} / <http://purl.org/dc/terms/language> wd:{self.q_language};
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
                p, data=data['lemmas'][self.lang_code]['value'], content=to_json(data))
        return p

    # def get_existing_lexemes(self) -> Dict[str, Dict[str, List]]:
    #     if not self.lexemes or not self.lexical_categories:
    #         return {}
    #     category_ids = self.lexical_categories.ids()
    #     # list of lexemes per grammatical category
    #     entities = list_to_dict_of_lists(
    #         (l for l in self.lexemes.get() if self.lang_code in l.lemmas and l.lexicalCategory in category_ids),
    #         lambda l: category_ids[l.lexicalCategory]
    #     )
    #     count = sum((len(v) for v in entities.values()))
    #     if count != len(self.lexemes.get()):
    #         print(f'{len(self.lexemes.get()) - count} entities have not been recognized')
    #     # convert all lists into lemma -> list, where most lists will just have one element
    #     return {
    #         k: list_to_dict_of_lists(v, lambda l: l.lemmas[self.lang_code].value)
    #         for k, v in entities.items()
    #     }
    #
