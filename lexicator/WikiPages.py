import dataclasses
import re
from dataclasses import dataclass
from html import unescape
from typing import List

from mwparserfromhell import parse as mw_parse
from pywikiapi import Site, AttrDict

from .Cache import CacheJsonl
from .consts import NS_TEMPLATE, NS_MAIN, re_template_names
from .utils import to_json, batches, extract_template_params, TemplateType

root_templates = {'inflection сущ ru', 'падежи'}


@dataclass
class WikiPage:
    title: str
    templates: List[TemplateType] = None
    content: str = None
    redirect: str = None


class WikiPages(CacheJsonl):
    def __init__(self, filename: str, site: Site):
        super().__init__(filename)
        self.site = site
        # noinspection SpellCheckingInspection
        self.re_html_comment = re.compile(r'<!--[\s\S]*?-->')
        self.re_noinclude = re.compile(r'<\s*noinclude\s*>([^<]*)<\s*/\s*noinclude\s*>')
        self.re_includeonly = re.compile(r'<\s*includeonly\s*>([^<]*)<\s*/\s*includeonly\s*>')
        self.object_hook = None

    def generate(self, append=False):
        titles = set()
        loaded_titles = set()
        if append:
            self._reload()
            if self._data:
                loaded_titles = {p.title for p in self._data}
        with open(self.filename, "a+" if append else "w+") as file:
            if append:
                print('', file=file)
            for batch in batches(self.get_all_relevant_pages(loaded_titles, append), 50):
                for res in self.load_pages(batch, titles):
                    print(to_json(res), file=file)

    def get_all_relevant_pages(self, skip_titles, append):
        raise ValueError('Must be derived')

    def load_pages(self, batch, titles=None):
        for query in self.site.query(
                prop=['revisions', 'info'],
                rvprop='content',
                rvslots='main',
                titles=batch,
                redirects=True,
        ):
            if 'pages' in query:
                for page in query.pages:
                    if titles and page.title in titles:
                        print(f'Duplicate title {page.title}')
                    else:
                        if titles:
                            titles.add(page.title)
                        yield self.parse_page(page)
            if 'redirects' in query:
                yield from (WikiPage(title=r['from'], redirect=r['to']) for r in query.redirects)

    def parse_page(self, page):
        text = None
        suspects = set()
        results: List[TemplateType] = []
        if 'revisions' in page and len(page.revisions) == 1 and 'slots' in page.revisions[0] and 'main' in \
                page.revisions[0].slots and 'content' in page.revisions[0].slots.main:
            text = page.revisions[0].slots.main.content
            text = self.re_html_comment.sub('', text)
            text = self.re_noinclude.sub('', text)
            text = self.re_includeonly.sub(r'\1', text)
            text = unescape(text)
            for val in extract_template_params(mw_parse(text)):
                if val[1] is not None:
                    if val not in results:
                        results.append(val)
                else:
                    suspects.add(val[0])

        if not results:
            msg = f'No templates found in {page.title}'
            for t in suspects:
                msg += f'\n  Suspected template: {t}'
            print(msg)

        return self.new_page(page, results, text)

    def new_page(self, page, templates, text):
        return WikiPage(title=page.title, templates=templates, content=text)

    def _reload(self):
        super()._reload()
        if self._data:
            # noinspection PyArgumentList
            self._data = [WikiPage(**v) for v in self._data
                          if 'template' not in v or re_template_names.match(v.template)]


class WikiPagesWords(WikiPages):
    def get_all_relevant_pages(self, skip_titles, append):
        titles = set()
        if append and not isinstance(append, bool):
            append = [append] if isinstance(append, str) else append
            generator = [AttrDict(transcludedin=[AttrDict(title=v) for v in append])]
        else:
            generator = self.site.query_pages(
                prop='transcludedin', tilimit='max', tinamespace=NS_MAIN,
                titles=['Template:' + w for w in root_templates])

        for page in generator:
            if 'transcludedin' in page:
                for p in page.transcludedin:
                    if p.title in skip_titles:
                        continue
                    if p.title in titles:
                        # print(f'Duplicate title returned: {p.title}')
                        continue
                    titles.add(p.title)
                    yield p.title

    def new_page(self, page, templates, text):
        return WikiPage(title=page.title, templates=templates)


class WikiPagesTemplates(WikiPages):
    def _reload(self):
        super()._reload()
        if not self._data:
            return
        result = []
        redirects = {}
        by_title = {}
        for r in self._data:
            if r.redirect:
                redirects[r.title] = r.redirect
            else:
                result.append(r)
                by_title[r.title] = r

        last_count = 0
        while len(redirects) != last_count:
            last_count = len(redirects)
            for frm in list(redirects.keys()):
                to = redirects[frm]
                if to in by_title:
                    target = by_title[to]
                    if not re.match(r'^Шаблон:', frm):
                        print(f'Unrecognized namespace for {frm}, skipping')
                        continue
                    result.append(dataclasses.replace(target, title=frm))
                    del redirects[frm]
        if redirects:
            print('Unable to find redirect targets')
            for k, v in redirects.items():
                print(f'  {k} => {v}')

        self._data = {w.title.split(':', 1)[1]: w for w in result}

    def get_all_relevant_pages(self, skip_titles, append):
        titles = set()
        if append and not isinstance(append, bool):
            append = [append] if isinstance(append, str) else append
            generator = [AttrDict(allpages=[AttrDict(title=v) for v in append])]
        else:
            generator = self.site.query(list='allpages', apnamespace=NS_TEMPLATE, aplimit='max')
        for q in generator:
            for p in q.allpages:
                if not re_template_names.match(p.title):
                    continue
                if p.title in skip_titles:
                    continue
                if p.title in titles:
                    # print(f'Duplicate title returned: {p.title}')
                    continue
                titles.add(p.title)
                yield p.title
