from __future__ import annotations

import dataclasses
import re
from typing import Dict, Union

from lexicator.consts import NS_TEMPLATE_NAME, lower_first_letter, wikipage_must_have, root_templates, \
    double_title_case, ignore_templates, re_template_names, re_ignore_template_prefixes, upper_first_letter
from lexicator.wikicache import PageFilter, ContentStore, LogConfig, PageContent
from .ParserState import ParserState
from .TemplateParser import TemplateParser
from .common import well_known_parameters, expand_template


class PageParser(PageFilter):
    # existing_entities: Dict[str, Dict[str, List]]

    def __init__(self, lang_code: str, source: ContentStore, wiki_templates: ContentStore,
                 log_config: LogConfig) -> None:
        super().__init__(log_config=log_config, source=source)
        self.lang_code = lang_code
        self.template_ns = NS_TEMPLATE_NAME[lang_code]
        self.template_ns_lc = lower_first_letter(self.template_ns)
        self.wiki_templates = wiki_templates
        self.templates_no_ns: Dict[str, PageContent] = {}
        self.re_wikipage_must_have = re.compile('|'.join((v for v in wikipage_must_have[lang_code])))
        self.root_templates = root_templates[lang_code]
        self.re_root_templates = re.compile('|'.join(self.root_templates))
        self.re_root_templates_full_str = re.compile(r'^(' + '|'.join(self.root_templates) + r')$')
        self.ignore_templates = double_title_case(ignore_templates[lang_code])
        self.re_template_names = re_template_names[lang_code]

        self.re_ignore_template_prefixes = re.compile(
            r'^(' + '|'.join(double_title_case(re_ignore_template_prefixes[lang_code])) + r')')

        self.re_well_known_parameters = [re.compile(r'^\s*(' + word + r')\s*$')
                                         for word in well_known_parameters[lang_code]]

        self.expand_template = {t: (lambda arg: False) for t in self.root_templates}
        for k, v in expand_template[lang_code].items():
            self.expand_template[k] = v
            self.expand_template[upper_first_letter(k)] = v

    def process_page(self, page: PageContent, force: Union[bool, str]) -> PageContent:
        if page.content and self.is_valid_page(page):
            state = ParserState(self, page, force)
            TemplateParser('', page.title, page.content, {}, state).parse_page()
            if state.warnings:
                print(f"Warnings for {page.title}:\n  " + '\n  '.join(state.warnings))
                content = '\n'.join(state.warnings)
            else:
                content = None
            return dataclasses.replace(page, data=state.result, content=content)

    def is_valid_page(self, page: PageContent):
        return self.re_wikipage_must_have.search(page.content) and (
                self.re_template_names.search(page.content)
                or
                self.re_root_templates.search(page.content)
        )
