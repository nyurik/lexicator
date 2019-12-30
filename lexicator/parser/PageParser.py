from __future__ import annotations

import dataclasses
import re
from typing import Dict, Union

from mwparserfromhell.nodes import Template, Text, Tag, Wikilink, HTMLEntity, Comment, ExternalLink

from lexicator.consts import root_templates, wikipage_must_have, ignore_templates, re_ignore_template_prefixes, \
    re_template_names, NS_TEMPLATE_NAME, NS_TEMPLATE, double_title_case, lower_first_letter
from lexicator.wikicache import ContentStore, PageContent, PageFilter, LogConfig
from .ParserState import ParserState
from .TemplateParser import TemplateParser

ignore_types = {Text, Tag, Wikilink, Comment, ExternalLink, HTMLEntity}


def params_to_dict(params):
    result = {}
    for p in params:
        value = str(p.value).strip()
        if value:
            result[str(p.name).strip()] = value
    return result


# noinspection PyUnusedLocal
def flag_template(self: TemplateParser, code, template: Template, flag, index=None):
    if index and template.has(index):
        param = template.get(index)
        self.apply_wikitext(param.value)
        code.replace(template, param)
    else:
        code.remove(template)
    if self.state.flags is None:
        self.state.flags = set()
    self.state.flags.add(flag)


custom_templates = {
    '-': lambda s, c, t: c.replace(t, '\u00a0— '),
    'PAGENAME': lambda s, c, t: c.replace(t, s.word),
    'NAMESPACE': lambda s, c, t: c.remove(t),
    'anchorencode:': lambda s, c, t: c.remove(t),
    'ns:0': lambda s, c, t: c.remove(t),
    'ns:Template': lambda s, c, t: c.replace(t, str(NS_TEMPLATE)),
}

# TODO
custom_templates2 = {
    'прост.': lambda s, c, t: flag_template(s, c, t, 'primitive'),
    'устар.': lambda s, c, t: flag_template(s, c, t, 'outdated'),
    'детск.': lambda s, c, t: flag_template(s, c, t, 'childish'),
    # эта форма слова или ударение является нестандартной для данной схемы словоизменения -- △
    'особ.ф.': lambda s, c, t: flag_template(s, c, t, 'unusual_form', '1'),
    'incorrect': lambda s, c, t: flag_template(s, c, t, 'incorrect', '1'),
}

# Do not expand any root templates other than the ones already listed above
expand_template = {t: (lambda arg: False) for t in root_templates['ru']}
expand_template['inflection сущ ru'] = lambda arg: arg.has('form') and str(arg.get('form').value).strip()
expand_template['Inflection сущ ru'] = expand_template['inflection сущ ru']

well_known_parameters = {'слоги', 'дореф'}
re_well_known_parameters = [re.compile(r'^\s*(' + word + r')\s*$') for word in well_known_parameters]
re_allowed_extras = re.compile(r'^[и, \n/!]+$')


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
