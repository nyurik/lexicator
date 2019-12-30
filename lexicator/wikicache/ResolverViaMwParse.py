from __future__ import annotations

import json
import re
from datetime import datetime
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
        for batch in batches(source, self.batch_size):
            vals = {str(i): (v, json.loads(v)) for i, v in enumerate(batch)}
            wikitext = ''
            for ind, val in vals.items():
                t_name, = val[1]
                if t_name != self.template_name:
                    raise ValueError(f"Unexpected template name {t_name} instead of {self.template_name}")
                t_params = val[1][t_name]
                t_params2 = {k: t_params[k] for k in t_params if k not in self.ignore_params}
                if t_params:
                    wikitext += f"* _INDEX_={ind}\n"
                    wikitext += str(Template(t_name, params=[Parameter(k, v) for k, v in t_params2.items()]))
                    wikitext += '\n'
                else:
                    yield PageContent(title=val[0], timestamp=datetime.utcnow(), data={})
            if not wikitext:
                continue
            wikitext += f"* _INDEX_=END\n"

            print(f"API: resolving {len(batch)} templates, text len={len(wikitext):,}, starting with {batch[0]}")
            text = self.site(
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

            result: Union[PageContent, None] = None
            for k, v in self.re_params.findall(text):
                if k == '_INDEX_':
                    if result:
                        if result.data:
                            yield result
                        else:
                            print(f'Empty result for {result.title}, skipping')
                    if v == 'END':
                        break
                    result = PageContent(title=vals[v][0], timestamp=datetime.utcnow(), data={})
                else:
                    result.data[k] = v

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
