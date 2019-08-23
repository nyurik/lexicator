from pywikiapi import Site

from .LexemeTemplateParser import LexemeTemplateParser
from .utils import PageContent
from .PageFilter import PageFilter
from .ContentStore import ContentStore


class LexemeMaker(PageFilter):

    def __init__(self, source: ContentStore, wikidata: Site, resolve_noun_ru, resolve_transcriptions_ru) -> None:
        super().__init__(source)
        self.source = source
        self.wikidata = wikidata
        self.resolve_noun_ru = resolve_noun_ru
        self.resolve_transcriptions_ru = resolve_transcriptions_ru

    def process_page(self, page: PageContent):
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

        return LexemeTemplateParser(page, self.resolve_noun_ru, self.resolve_transcriptions_ru).run(), None
