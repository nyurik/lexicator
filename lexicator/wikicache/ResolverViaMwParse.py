from __future__ import annotations

import json
import re
from datetime import datetime
from itertools import islice
from typing import List, Iterable, Tuple, Union, Callable, Dict, TYPE_CHECKING

from mwparserfromhell.nodes import Template
from mwparserfromhell.nodes.extras import Parameter

from .PageContent import PageContent
from .PageRetriever import PageRetriever
from .utils import batches, json_key, LogConfig, MwSite

if TYPE_CHECKING:
    from .ContentStore import ContentStore


class ResolverViaMwParse(PageRetriever):
    """
    In Wiktionary, there are many templates that simply convert parameters into parameters
    for some other template for printing. In Wikipedia, there could be many infobox templates,
    such as one for music and one for movies, but both call the basic "infobox" template
    with some parameters.  This code allows one to get those internal "infobox" parameters.

    For example, a {{сущ-ru|чайха́нщица|жо 5a}} ru.wiktionary template creates all noun
    forms for a russian noun "чайха́нщица", according to "жо 5a" ru-word classification.
    Internally {{сущ-ru}} calls {{inflection/ru/noun}} to which it passes all noun forms
    as individual parameters, expecting inflection/ru/noun to create a noun wiki table.
    Parsing wiki table HTML is difficult and error prone, so instead, this code injects
    a fake implementation of the inflection/ru/noun template, which creates a list
    of <li>...</li> text. Each list element contains the name of the parameter and
    the parameter's value."""

    # Result types:
    # <li>acc-pl=чайха́нщиц<sup>^</sup></li>
    re_params = re.compile(r'<li>([^=<]+)=(.+?)</li>')

    def __init__(self, site: MwSite, template_source: ContentStore, batch_size: int,
                 template_name: str, internal_template: str, ignore_params: List[str], output_params: List[str],
                 log_config: LogConfig = None):
        super().__init__(log_config=log_config, is_remote=True)
        self.site = site
        self.template_source = template_source
        self.batch_size = batch_size
        self.template_name = template_name
        self.ignore_params = set(ignore_params)
        self.output_params = output_params
        # Convert each arg into wikitext  "* acc-pl={{{acc-pl|}}}"
        self.internal_template = 'Template:' + internal_template
        self.template_sandbox_text = ''.join(
            ("{{#if:{{{" + v + "|}}}|\n* " + v + "={{{" + v + "|}}}}}" for v in output_params))

    @property
    def follow_redirects(self) -> bool:
        return False

    def find_recent_changes(self, last_change: datetime) -> Iterable[Tuple[str, datetime]]:
        return []

    def get_titles(self,
                   source: Iterable[str],
                   force: Union[bool, str],
                   progress_reporter: Callable[[str], None] = None) -> Iterable[PageContent]:
        if not self.site:
            return []

        min_batch_size = 15
        source_iter = iter(source)
        batch_size = self.batch_size
        while True:
            # take first batch_size items, where batch_size could be adjusted in subsequent calls
            batch = list(islice(source_iter, batch_size))
            if not batch:
                break
            pages, skipped = self.process_batch(batch)
            yield from pages
            if skipped and batch_size > min_batch_size:
                batch_size = max(min_batch_size, batch_size - len(skipped) - 1)
                print(f"Reduced batch size for {self.template_name} to {batch_size} because of {len(skipped)} skipped")
            all_ignored = []
            while skipped:
                batch = skipped[:min_batch_size]
                del skipped[:min_batch_size]
                pages, ignored = self.process_batch(batch)
                yield from pages
                all_ignored.extend(ignored)
            if all_ignored:
                prefix = "\n* "
                print(f"Ignoring empty results: {prefix}{prefix.join(all_ignored)}")

    def process_batch(self, batch: List[str]) -> Tuple[List[PageContent], List[str]]:
        vals = {str(i): (v, json.loads(v)) for i, v in enumerate(batch)}
        results, wikitext, first_page = self.create_wikitext(vals)
        if results:
            print(f'Skipping {len(results):,} empty pages starting with {results[0].title}')
        if not wikitext:
            return results, []
        print(f"API: resolving {len(batch) - len(results)} templates, text len={len(wikitext):,}, "
              f"starting with {first_page}")
        text = self.call_parse_api(wikitext)
        skipped: List[str] = []
        result: Union[PageContent, None] = None
        for k, v in self.re_params.findall(text):
            if k == '_INDEX_':
                if result:
                    if result.data:
                        results.append(result)
                    else:
                        skipped.append(result.title)
                if v == 'END':
                    break
                result = PageContent(title=vals[v][0], timestamp=datetime.utcnow(), data={})
            else:
                result.data[k] = v
        return results, skipped

    def call_parse_api(self, wikitext):
        return self.site(
            'parse',
            text=wikitext,
            prop='text',
            contentmodel='wikitext',
            contentformat='text/x-wiki',
            templatesandboxcontentmodel='wikitext',
            templatesandboxcontentformat='text/x-wiki',
            templatesandboxtitle=self.internal_template,
            templatesandboxtext=self.template_sandbox_text,
        ).parse.text

    def create_wikitext(self, vals):
        wikitext = ''
        empty_pages = []
        first_page = ''
        for ind, val in vals.items():
            t_name, = val[1]
            if t_name != self.template_name:
                raise ValueError(f"Unexpected template name {t_name} instead of {self.template_name}")
            t_params = val[1][t_name]
            t_params2 = {k: t_params[k] for k in t_params if k not in self.ignore_params}
            if t_params:
                if not first_page:
                    first_page = val[0]
                wikitext += f"* _INDEX_={ind}\n"
                wikitext += str(Template(t_name, params=[Parameter(k, v) for k, v in t_params2.items()]))
                wikitext += '\n'
            else:
                empty_pages.append(PageContent(title=val[0], timestamp=datetime.utcnow(), data={}))
        if wikitext:
            wikitext += f"* _INDEX_=END\n"
        return empty_pages, wikitext, first_page

    def get_all_titles(self, progress_reporter: Callable[[str], None], exclude: Dict[str, datetime] = None,
                       filters=None) -> Iterable[PageContent]:
        pass

    def can_refresh(self) -> bool:
        return False

    def custom_refresh(self, filters=None) -> Iterable[str]:
        for page in self.template_source.get_all(filters=filters):
            if page.data:
                for dat in page.data:
                    if dat[1] == self.template_name:
                        yield json_key(dat[1], dat[2])
