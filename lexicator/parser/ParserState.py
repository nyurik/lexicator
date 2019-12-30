from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from typing import List

from lexicator.wikicache import PageContent
from .PageParser import PageParser


@dataclass
class ParserState:
    def __init__(self, page_parser: PageParser, page: PageContent, force) -> None:
        self.page_parser = page_parser
        self.page = page
        self.force = force

        self.flags = None
        self.warnings = []
        self.result = []
        self.header: List[str] = []

    def get_template(self, name):
        templates_no_ns = self.page_parser.templates_no_ns
        if not templates_no_ns:
            templates_no_ns.update(
                {v.title.split(':', 1)[1]: v for v in self.page_parser.wiki_templates.get_all() if ':' in v.title})
        if not self.force and name in templates_no_ns:
            return templates_no_ns[name]
        page = None
        for page in self.page_parser.wiki_templates.get_multiple([self.page_parser.template_ns + name],
                                                                 force=self.force):
            break
        templates_no_ns[name] = page
        return page

    def add_result(self, name, params):
        if isinstance(params, dict):
            params = {k: unescape(v) for k, v in params.items()}
        self.result.append((self.header[:], name, params,))
