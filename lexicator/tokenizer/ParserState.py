from __future__ import annotations

import re
from dataclasses import dataclass
from html import unescape
from typing import List, TYPE_CHECKING, Dict, Tuple, Union, Set

from lexicator.wikicache import PageContent

if TYPE_CHECKING:
    from .PageParser import PageParser

re_title_space_normalizer = re.compile(r'[ _]+')

@dataclass
class ParserState:
    def __init__(self, page_parser: PageParser, page: PageContent, force: bool) -> None:
        self.page_parser: PageParser = page_parser
        self.page: PageContent = page
        self.force: bool = force

        self.flags: Set[str] = set()
        self.warnings: List[str] = []
        self.result: List[Tuple[List[str], str, Union[str, Dict[str, str]]]] = []
        self.header: List[Union[str, dict]] = []

    def get_template(self, name: str):
        templates_no_ns = self.page_parser.templates_no_ns
        if not templates_no_ns:
            templates_no_ns.update(
                {v.title.split(':', 1)[1]: v for v in self.page_parser.wiki_templates.get_all() if ':' in v.title})
        if not self.force and name in templates_no_ns:
            return templates_no_ns[name]
        name = re_title_space_normalizer.sub(' ', name)
        if not self.force and name in templates_no_ns:
            return templates_no_ns[name]
        page = None
        for page in self.page_parser.wiki_templates.get_multiple([self.page_parser.template_ns + name],
                                                                 force=self.force):
            break
        templates_no_ns[name] = page
        return page

    def add_result(self, name: str, params: Union[Dict[str, str], str]):
        if isinstance(params, dict):
            params = {k: unescape(v) for k, v in params.items()}
        self.result.append((self.header[:], name, params,))
