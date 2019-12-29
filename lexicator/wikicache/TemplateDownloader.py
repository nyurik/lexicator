import dataclasses
import re
from html import unescape
from typing import Callable, Union

from lexicator.wikicache.PageContent import PageContent
from lexicator.wikicache.WikipageDownloader import WikipageDownloader
from lexicator.consts.consts import NS_TEMPLATE
from lexicator.wikicache.utils import LogConfig, MwSite


class TemplateDownloader(WikipageDownloader):
    def __init__(self, site: MwSite, title_filter: Callable[[int, str], bool] = None, log_config: LogConfig = None):
        super().__init__(site=site, namespace=NS_TEMPLATE, title_filter=title_filter, store_redirects=True,
                         log_config=log_config)

        # noinspection SpellCheckingInspection
        self.re_html_comment = re.compile(r'<!--[\s\S]*?-->')
        self.re_noinclude = re.compile(r'<\s*noinclude\s*>([^<]*)<\s*/\s*noinclude\s*>')
        self.re_includeonly = re.compile(r'<\s*includeonly\s*>([^<]*)<\s*/\s*includeonly\s*>')

    def to_content(self, page) -> Union[PageContent, None]:
        p = super().to_content(page)
        if p:
            text = p.content
            text = self.re_html_comment.sub('', text)
            text = self.re_noinclude.sub('', text)
            text = self.re_includeonly.sub(r'\1', text)
            text = unescape(text)
            return dataclasses.replace(p, content=text)
