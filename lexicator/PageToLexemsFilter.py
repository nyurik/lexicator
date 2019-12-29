import dataclasses
from typing import Dict, Union

from pywikiapi import Site

from lexicator.ContentStore import ContentStore
from lexicator.PageFilter import PageFilter
from lexicator.PageToLexeme import PageToLexeme
from lexicator.utils import PageContent, Config


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
            if row[1] == '_заголовок' or row[1] == '_з':
                if not has_first_section:
                    has_first_section = True
                else:
                    sections.append(data_section)
                    data_section = []
            data_section.append(row)
        sections.append(data_section)

        results = []
        errors = []
        for section in sections:
            parser = PageToLexeme(page.title, section, self.resolvers)
            try:
                results.append(parser.run())
            except ValueError as err:
                errors.append(str(err))

        if not results:
            results = None

        if errors:
            errors = '\n\n**************************************\n'.join(errors)
        elif not results:
            errors = 'Nothing was found to process'
        else:
            errors = None

        return dataclasses.replace(page, data=results, content=errors)
