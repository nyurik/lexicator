import dataclasses

from pywikiapi import Site
from typing import Dict, Union, Iterable

from .PageToLexeme import PageToLexeme
from .utils import PageContent, Config
from .PageFilter import PageFilter
from .ContentStore import ContentStore


class PageToLexemsFilter(PageFilter):

    def __init__(self, config: Config, source: ContentStore, wikidata: Site,
                 resolvers: Dict[str, ContentStore]) -> None:
        super().__init__(config, source)
        self.source = source
        self.wikidata = wikidata
        self.resolvers = resolvers
        self.handled_types = {'noun', 'adjective', 'participle'}

    def process_page(self, page: PageContent, force: Union[bool, str]) -> Union[PageContent, None]:
        if not page.data:
            return None

        sections = []
        data_section = []
        has_first_section = False
        for row in page.data:
            if row[1] == '_заголовок':
                if not has_first_section:
                    has_first_section = True
                else:
                    sections.append(data_section)
                    data_section = []
            data_section.append(row)
        sections.append(data_section)

        results = []
        for section in sections:
            parser = PageToLexeme(page.title, section, self.resolvers)
            try:
                results.append(parser.run())
            except ValueError as err:
                if parser.grammar_types.intersection(self.handled_types):
                    raise

        if results:
            return dataclasses.replace(page, data=results, content=None)
