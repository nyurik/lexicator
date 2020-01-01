from __future__ import annotations

import dataclasses
import re
from typing import Dict, Union, Set

from lexicator.consts import MEANING_HEADERS, handled_types, known_headers
from lexicator.wikicache import ContentStore, PageContent, LogConfig, PageFilter, MwSite
from .PageToLexeme import PageToLexeme
from .common import resolver_classes


class PageToLexemsFilter(PageFilter):
    def __init__(self, log_config: LogConfig, site: MwSite, source: ContentStore) -> None:
        super().__init__(log_config, source)
        self.lang_code: str = site.lang_code
        self.source: ContentStore = source
        self.handled_types: Set[str] = handled_types[self.lang_code]
        self.meanings_headers: Set[str] = set((f"_{v}" for v in MEANING_HEADERS[self.lang_code]))

        self.known_headers = known_headers[self.lang_code]
        self.known_headers[tuple()] = 'root'

        retrievers = [v(log_config, site, source) for v in resolver_classes[self.lang_code]]
        non_letters = r'[^\w-]'

        self.resolvers: Dict[str, ContentStore] = {
            v.template_name:
                ContentStore(source.filename.parent / f"resolve_{re.sub(non_letters, '_', v.template_name)}.db", v)
            for v in retrievers}

    def before_refresh(self, filters=None):
        for v in self.resolvers.values():
            v.custom_refresh(filters)

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
                parser = PageToLexeme(self, page.title, section)
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
