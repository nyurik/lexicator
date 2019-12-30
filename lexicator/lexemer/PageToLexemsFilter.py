from __future__ import annotations

import dataclasses
from typing import Dict, Union, TYPE_CHECKING

from lexicator.consts import MEANING_HEADERS
from lexicator.wikicache import PageFilter
from .PageToLexeme import PageToLexeme
from .languages import handled_types

if TYPE_CHECKING:
    from lexicator.wikicache import ContentStore, PageContent, LogConfig


class PageToLexemsFilter(PageFilter):
    def __init__(self, log_config: LogConfig, lang_code: str, source: ContentStore,
                 resolvers: Dict[str, ContentStore]) -> None:
        super().__init__(log_config, source)
        self.lang_code = lang_code
        self.source = source
        self.resolvers = resolvers
        self.handled_types = handled_types[lang_code]
        self.meanings_headers = set((f"_{v}" for v in MEANING_HEADERS[lang_code]))

    # noinspection PyUnusedLocal
    def process_page(self, page: PageContent, force: Union[bool, str]) -> Union[PageContent, None]:
        if not page.data:
            return None

        sections = []
        data_section = []
        has_first_section = False
        for row in page.data:
            if row[1] in self.meanings_headers:
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
            try:
                parser = PageToLexeme(self.lang_code, page.title, section, self.resolvers)
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
