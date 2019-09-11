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
        if page.data:
            parser = PageToLexeme(page, self.resolvers)
            try:
                return parser.run()
            except ValueError as err:
                if parser.grammar_types.intersection(self.handled_types):
                    if self.config.print_warnings:
                        print(err)
                    raise
