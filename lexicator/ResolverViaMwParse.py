import json
import re
from datetime import datetime
from typing import Iterable, Callable, Dict, Tuple, List, Union

from pywikiapi import Site

from lexicator.PageRetriever import PageRetriever
from lexicator.utils import PageContent, batches, params_to_wikitext, Config


def json_key(template, params):
    return json.dumps({template: params}, ensure_ascii=False, separators=(',', ':'), sort_keys=True)


class ResolverViaMwParse(PageRetriever):
    """
    Use action=parse to convert {{сущ-ru}} template invocation, e.g.  {{сущ-ru|чайха́нщица|жо 5a}}
    into an html with a list of <li>...</li> text. Each element would contain the name of
    the argument and the argument's value.  The output is generated in this format
    because internally {{сущ-ru}} calls {{inflection/ru/noun}} to which it passes
    all those parameters. We just print them by overriding the internal template
    using the templatesandboxtitle parameter.
    These arguments also requires the "text" param."""

    # Result types:
    # <li>acc-pl=чайха́нщиц<sup>^</sup></li>
    re_params = re.compile(r'<li>([^=<]+)=(.+?)</li>')

    def __init__(self, config: Config, site: Site, template_source: 'ContentStore', batch_size: int,
                 template_name: str, internal_template: str, ignore_params: List[str], output_params: List[str]):
        super().__init__(config, is_remote=True)
        self.site = site
        self.template_source = template_source
        self.batch_size = batch_size
        self.template_name = template_name
        self.ignore_params = set(ignore_params)
        self.output_params = output_params
        # Convert each arg into wikitext  "* acc-pl={{{acc-pl|}}}"
        self.internal_template = 'Шаблон:' + internal_template
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
                    wikitext += params_to_wikitext((t_name, t_params2))
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

            result: PageContent = None
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


class ResolveNounRu(ResolverViaMwParse):
    def __init__(self, config: Config, template_source: 'ContentStore'):
        super().__init__(config, config.wiktionary, template_source, 150, 'сущ-ru', 'inflection/ru/noun', ['слоги'], [
            'acc-pl', 'acc-pl2', 'acc-sg', 'acc-sg-f', 'acc-sg2', 'case', 'dat-pl', 'dat-pl2', 'dat-sg', 'dat-sg-f',
            'dat-sg2', 'form', 'gen-pl', 'gen-pl2', 'gen-sg', 'gen-sg-f', 'gen-sg2', 'hide-text', 'ins-pl', 'ins-pl2',
            'ins-sg', 'ins-sg-f', 'ins-sg2', 'loc-sg', 'nom-pl', 'nom-pl2', 'nom-sg', 'nom-sg-f', 'nom-sg2', 'obelus',
            'prp-pl', 'prp-pl2', 'prp-sg', 'prp-sg-f', 'prp-sg2', 'prt-sg', 'pt', 'st', 'voc-sg', 'дореф', 'зализняк',
            'зализняк-1', 'зализняк-2', 'зализняк1', 'затрудн', 'зачин', 'кат', 'клитика', 'коммент', 'П', 'Пр', 'род',
            'скл', 'слоги', 'Сч', 'фам', 'чередование', 'шаблон-кат'])


class ResolveTranscriptionRu(ResolverViaMwParse):
    def __init__(self, config: Config, template_source: 'ContentStore'):
        super().__init__(config, config.wiktionary, template_source, 1000, 'transcription-ru', 'transcription', [],
                         ['1', '2', 'lang', 'источник', 'норма'])


class ResolveTranscriptionsRu(ResolverViaMwParse):
    def __init__(self, config: Config, template_source: 'ContentStore'):
        super().__init__(config, config.wiktionary, template_source, 500, 'transcriptions-ru', 'transcriptions', [],
                         ['1', '2', '3', '4', 'lang', 'источник', 'мн2', 'норма'])
