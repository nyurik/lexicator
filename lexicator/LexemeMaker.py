from pywikiapi import Site
from typing import Dict, Union

from .TemplateParser import TemplateParser
from .utils import PageContent, Config
from .PageFilter import PageFilter
from .ContentStore import ContentStore


class LexemeMaker(PageFilter):

    def __init__(self, config: Config, source: ContentStore, wikidata: Site,
                 resolvers: Dict[str, ContentStore]) -> None:
        super().__init__(config, source)
        self.source = source
        self.wikidata = wikidata
        self.resolvers = resolvers

    def process_page(self, page: PageContent, force: Union[bool, str]):
        if not page.data:
            return

        words = set()
        for header, template, params in page.data:
            if len(header) < 2 or header[1] != 'Морфологические и синтаксические свойства':
                continue
            words.add(header[0])

        if len(words) > 1:
            print(f"{page.title} has non-single header1 sections {words}")
            return
        elif not words:
            return

        return TemplateParser(page, self.resolvers).run(), None
