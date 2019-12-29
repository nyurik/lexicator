from __future__ import annotations

import dataclasses
import re
from dataclasses import dataclass
from html import unescape
from typing import Dict, Union, List

from mwparserfromhell import parse as mw_parse
# noinspection PyProtectedMember
from mwparserfromhell.nodes import Argument, Template, Text, Tag, Wikilink, Heading, HTMLEntity, Comment, ExternalLink
from mwparserfromhell.nodes.extras import Parameter

from lexicator.consts.common import root_templates, wikipage_must_have, ignore_templates, re_ignore_template_prefixes, \
    re_template_names, ignore_pages_if_template, MEANING_HEADERS
from lexicator.consts.utils import double_title_case
from lexicator.wikicache.ContentStore import ContentStore
from lexicator.wikicache.PageContent import PageContent
from lexicator.wikicache.PageFilter import PageFilter
from lexicator.consts.consts import NS_TEMPLATE
from lexicator.wikicache.utils import LogConfig

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
        self.wiki_templates = wiki_templates
        self.templates_no_ns: Dict[str, PageContent] = {}
        self.re_wikipage_must_have = re.compile('|'.join((v for v in wikipage_must_have[lang_code])))
        self.root_templates = root_templates[lang_code]
        self.re_root_templates = re.compile('|'.join(self.root_templates))
        self.re_root_templates_full_str = re.compile(r'^(' + '|'.join(self.root_templates) + r')$')
        self.ignore_templates = double_title_case(ignore_templates[lang_code])
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
                re_template_names[self.lang_code].search(page.content)
                or
                self.re_root_templates.search(page.content)
        )


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
        for page in self.page_parser.wiki_templates.get_multiple(['Шаблон:' + name], force=self.force):
            break
        templates_no_ns[name] = page
        return page

    def add_result(self, name, params):
        if isinstance(params, dict):
            params = {k: unescape(v) for k, v in params.items()}
        self.result.append((self.header[:], name, params,))


class TemplateParser:
    def __init__(self, template_name: str, word: str, content: str, arguments, state: ParserState) -> None:
        self.template_name = template_name
        self.word = word
        self.content = content
        self.arguments = arguments
        self.state = state

    def run(self):
        # print(f'\n------------------ {self.word}: "{self.template_name}" ----------------------')
        code = mw_parse(self.content)
        self.apply_wikitext(code)
        return code

    def parse_page(self):
        code = mw_parse(self.content)

        for ru_section in code.get_sections(levels=[1], matches=r'\{\{\s*-ru-\s*\}\}', include_headings=False):
            self.state.header = []
            self.parse_section(code, ru_section)

    def parse_section(self, code, section):
        for arg in section.filter(recursive=False):
            typ = type(arg)
            if typ in ignore_types:
                continue
            elif typ == Template:
                self.apply_wikitext(arg.name)
                name = str(arg.name).strip()
                if name in self.state.page_parser.ignore_templates:
                    continue
                name = self.to_template_name(name)
                if name in self.state.page_parser.ignore_templates:
                    continue
                if name in ignore_pages_if_template['ru']:
                    return None  # ignore these pages

                root_match = self.state.page_parser.re_root_templates_full_str.match(name)
                if root_match or re_template_names[self.state.page_parser.lang_code].match(name):
                    # Remove well-known params
                    for param in list(arg.params):
                        param_name = str(param.name)
                        for re_param in re_well_known_parameters:
                            m = re_param.match(param_name)
                            if not m:
                                continue
                            extras = ''
                            has_templates = False
                            for arg2 in param.value.filter(recursive=False):
                                argtyp = type(arg2)
                                if argtyp == Text:
                                    extras += arg2.value
                                elif argtyp == Template and str(arg2.name) in self.state.page_parser.root_templates:
                                    has_templates = True
                                elif argtyp == Wikilink:
                                    extras += str(arg2.text) if arg2.text else str(arg2.title)
                                elif argtyp != Comment:
                                    raise ValueError(f"cannot parse well known param {str(param).strip()}")
                            extras = extras.strip()
                            if has_templates and extras != '' and not re_allowed_extras.match(extras):
                                raise ValueError(f"well known param '{str(param).strip()}' has text and templates")
                            if has_templates:
                                self.parse_section(code, param.value)
                            elif extras:
                                self.state.add_result('_' + m.group(1), param.value.strip())
                            arg.remove(param)
                    if root_match:
                        self.state.add_result(name, params_to_dict(arg.params))
                        code.remove(arg)
                    else:
                        new_arg = self.apply_value(code, arg)
                        if new_arg:
                            self.parse_section(code, new_arg)

                elif not self.state.page_parser.re_ignore_template_prefixes.match(name):
                    self.warn(f"{self.state.header} {self.word}: Unknown template {arg}")
            elif typ == Heading:
                if len(self.state.header) < arg.level - 2:
                    self.state.header += [None] * (arg.level - 2 - len(self.state.header))
                else:
                    self.state.header = self.state.header[:arg.level - 2]
                self.apply_wikitext(arg.title)
                template = None
                templates = arg.title.filter_templates(recursive=False)
                if len(templates) == 1:
                    name = str(templates[0].name).strip()
                    if name in MEANING_HEADERS[self.state.page_parser.lang_code]:
                        template = {name: params_to_dict(templates[0].params)}
                        code.remove(templates[0])
                if templates and not template:
                    print(f"{self.state.header} {self.word} unrecognized header template in {arg.title}")
                text = str(arg.title).strip()
                if template:
                    if text:
                        print(f"{self.state.header} {self.word} has text '{text}' in addition to template {template}")
                        template['text'] = text
                    self.state.header.append(template)
                else:
                    self.state.header.append(text)
            else:
                self.warn(f"{self.state.header} {self.word}: Ha? {typ}  {arg}")

    @staticmethod
    def to_template_name(name):
        if name.startswith('Шаблон:') or name.startswith('шаблон:'):
            return name[len('шаблон:'):]
        elif name.startswith('Template:') or name.startswith('template:'):
            return name[len('template:'):]
        else:
            return name

    def apply_wikitext(self, code):
        if code:
            # print(str(code).replace('\n', '\\n')[:100])
            for arg in code.filter(recursive=False):
                self.apply_value(code, arg)

    def apply_value(self, code, arg):
        typ = type(arg)
        if typ == Text:
            return
        elif typ == Argument:
            self.apply_wikitext(arg.name)
            arg_name = str(arg.name)
            if arg_name in self.arguments:
                code.replace(arg, self.arguments[arg_name])
            elif arg.default is not None:
                self.apply_wikitext(arg.default)
                code.replace(arg, str(arg.default).strip())
        elif typ == Template:
            self.apply_wikitext(arg.name)
            name = self.to_template_name(str(arg.name).strip())
            if name == '':
                self.warn(f"Template name is blank in {arg}")
                code.remove(arg)
                return
            if name.startswith('safesubst:'):
                name = name[len('safesubst:'):].strip()
            if name.startswith('#'):
                if name.startswith('#if:'):
                    self.repl_conditional(
                        arg, code, 2 if len(arg.name.nodes) == 1 or arg.name.get(1).strip() == '' else 1)
                elif name.startswith('#ifeq:'):
                    if not arg.has('1'):
                        code.remove(arg)
                    else:
                        val1 = name[len('#ifeq:'):].strip()
                        val2 = arg.get('1')
                        self.apply_wikitext(val2.value)
                        val2 = str(val2.value).strip()
                        self.repl_conditional(arg, code, 3 if val1 == val2 else 2)
                elif name.startswith('#switch:'):
                    key = name[len('#switch:'):].strip()
                    if not arg.has(key):
                        key = '#default'
                        if not arg.has(key):
                            key = '1'
                            # if not arg.has(key):
                            #     self.warn(f'switch value "{key}" not found in {arg}')
                    self.repl_conditional(arg, code, key)
                elif name.startswith('#ifexist:'):
                    key = name[len('#ifexist:'):].strip().replace('Шаблон:', '').strip()
                    self.repl_conditional(arg, code, 1 if key in self.state.page_parser.templates_no_ns else 2)
                else:
                    raise ValueError(f'Unhandled special {name}')
            else:
                for param in arg.params:
                    self.apply_value(code, param)
                if name in custom_templates:
                    custom_templates[name](self, code, arg)
                elif (name in expand_template and not expand_template[name](arg)) or \
                        name in self.state.page_parser.ignore_templates:
                    # self.warn(f"Template {name} should not be expanded")
                    return
                else:
                    template_page = self.state.get_template(name)
                    if template_page:
                        sub_template_params = params_to_dict(arg.params)
                        self.state.add_result('_' + name, sub_template_params)
                        new_text = TemplateParser(
                            f'{self.template_name}.{name}', self.word, template_page.content,
                            sub_template_params, self.state).run()
                        new_arg = mw_parse(str(new_text).strip())
                        code.replace(arg, new_arg)
                        return new_arg
                    else:
                        self.warn(f"Template {name} is not known")
        elif typ == Parameter:
            self.apply_wikitext(arg.name)
            self.apply_wikitext(arg.value)
        elif typ == Tag:
            if str(arg.tag).strip() == 'noinclude':
                code.remove(arg)
            else:
                self.apply_wikitext(arg.contents)
        elif typ == Wikilink:
            self.apply_wikitext(arg.title)
            self.apply_wikitext(arg.text)
        elif typ == Heading:
            self.apply_wikitext(arg.title)
        elif typ == HTMLEntity:
            code.replace(arg, unescape(str(arg)))
        elif typ == Comment:
            code.remove(arg)
        elif typ == ExternalLink:
            return
        else:
            raise ValueError(f'Unknown type {typ} in {arg}')

    def repl_conditional(self, arg, code, index):
        if arg.has(index):
            param = arg.get(index)
            self.apply_wikitext(param.value)
            code.replace(arg, str(param.value).strip() if param.showkey else param.value)
        else:
            code.remove(arg)

    def warn(self, message):
        self.state.warnings.append(message)
