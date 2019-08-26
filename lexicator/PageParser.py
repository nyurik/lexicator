import re
from dataclasses import dataclass
from html import unescape
from typing import Dict, Iterable, Union

from mwparserfromhell import parse as mw_parse
# noinspection PyProtectedMember
from mwparserfromhell.nodes import Argument, Template, Text, Tag, Wikilink, Heading, HTMLEntity, Comment, ExternalLink
from mwparserfromhell.nodes.extras import Parameter

from lexicator.consts import root_header_templates, ignore_templates, re_ignore_template_prefixes
from .ContentStore import ContentStore
from .PageFilter import PageFilter
from .consts import root_templates, NS_TEMPLATE, known_fields, re_template_names, \
    re_known_headers, re_root_templates, re_root_templates_full_str
from .utils import PageContent, Config

ignore_types = {Text, Tag, Wikilink, Comment, ExternalLink, HTMLEntity}


@dataclass
class SpecialTemplate:
    flag: str
    action: str


def params_to_dict(params):
    result = {}
    for p in params:
        value = str(p.value).strip()
        if value:
            result[str(p.name).strip()] = value
    return result


# noinspection PyUnusedLocal
def flag_template(self: 'TemplateParser', code, template: Template, flag, index=None):
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
    # 'по-слогам': syllables,
    # 'по слогам': syllables,
    # 'слоги': syllables2,
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
expand_template = {t: (lambda arg: False) for t in root_templates}
expand_template['inflection сущ ru'] = lambda arg: arg.has('form') and str(arg.get('form').value).strip()
expand_template['Inflection сущ ru'] = expand_template['inflection сущ ru']

well_known_parameters = {'слоги', 'дореф'}
re_well_known_parameters = [re.compile(r'^\s*(' + word + r')\s*$') for word in well_known_parameters]


class PageParser(PageFilter):
    # existing_entities: Dict[str, Dict[str, List]]

    def __init__(self,
                 config: Config,
                 source: ContentStore,
                 parse_fields: Iterable[str],
                 wiki_templates: ContentStore,
                 ) -> None:
        super().__init__(config, source)
        self.fields = set(v for v in known_fields if v.name in parse_fields) if parse_fields else known_fields
        self.wiki_templates = wiki_templates
        self.templates_no_ns: Dict[str, PageContent] = {}

    def process_page(self, page: PageContent, force: Union[bool, str]):
        if page.content and re_known_headers.search(page.content) and (
                re_template_names.search(page.content) or
                re_root_templates.search(page.content)):
            state = ParserState(page, self.wiki_templates, self.templates_no_ns, force)
            data = TemplateParser('', page.title, page.content, {}, state).parse_page()
            if state.warnings:
                print(f"Warnings for {page.title}:\n  " + '\n  '.join(state.warnings))
                return data, '\n'.join(state.warnings)
            else:
                return data, None


@dataclass
class ParserState:
    def __init__(self, page: PageContent, wiki_templates: ContentStore,
                 templates_no_ns: Dict[str, PageContent], force) -> None:
        self.flags = None
        self.page = page
        self.warnings = []
        self.wiki_templates = wiki_templates
        self.templates_no_ns = templates_no_ns
        self.force = force

    def get_template(self, name):
        if not self.templates_no_ns:
            self.templates_no_ns.update({v.title.split(':', 1)[1]: v for v in self.wiki_templates.get_all()})
        if not self.force and name in self.templates_no_ns:
            return self.templates_no_ns[name]
        page = None
        for page in self.wiki_templates.get_multiple(['Шаблон:' + name], force=self.force):
            break
        self.templates_no_ns[name] = page
        return page


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
        result = []
        code = mw_parse(self.content)

        for ru_section in code.get_sections(levels=[1], matches=r'\{\{\s*-ru-\s*\}\}', include_headings=False):
            header = []
            self.parse_section(code, header, ru_section, result)
        return result

    def parse_section(self, code, header, section, result):
        for arg in section.filter(recursive=False):
            typ = type(arg)
            if typ in ignore_types:
                continue
            elif typ == Template:
                self.apply_wikitext(arg.name)
                name = str(arg.name).strip()
                if name in ignore_templates:
                    continue
                if name.startswith('Шаблон:') or name.startswith('шаблон:'):
                    name = name[len('шаблон:'):]
                if name in ignore_templates:
                    continue

                root_match = re_root_templates_full_str.match(name)
                if root_match or re_template_names.match(name):
                    # Remove well-known params
                    result_size = len(result)
                    for param in list(arg.params):
                        param_name = str(param.name)
                        for re_param in re_well_known_parameters:
                            m = re_param.match(param_name)
                            if not m:
                                continue
                            extras = ''
                            has_templates = False
                            for arg2 in param.value.filter(recursive=False):
                                if type(arg2) == Text:
                                    extras += arg2.value
                                elif type(arg2) == Template and str(arg2.name) in root_templates:
                                    has_templates = True
                                else:
                                    raise ValueError(f"cannot parse well known param {param}")
                            extras = extras.strip()
                            if has_templates and extras != '':
                                raise ValueError(f"well known param '{param}' has text and templates")
                            if has_templates:
                                self.parse_section(code, header, param.value, result)
                            elif extras:
                                result.append((header[:], '_' + m.group(1), param.value.strip(),))
                            arg.remove(param)
                    result_size2 = len(result)
                    if root_match:
                        result.append((header[:], name, params_to_dict(arg.params),))
                        code.remove(arg)
                    else:
                        new_arg = self.apply_value(code, arg)
                        self.parse_section(code, header, new_arg, result)
                    if result_size < result_size2 < len(result):
                        new_items = result[result_size2:]
                        del result[result_size2:]
                        result[result_size:result_size] = new_items

                elif name == 'к удалению':
                    return None  # ignore these pages
                elif not re_ignore_template_prefixes.match(name):
                    self.warn(f"{header} {self.word}: Unknown template {arg}")
            elif typ == Heading:
                if len(header) < arg.level - 2:
                    header += [None] * (arg.level - 2 - len(header))
                else:
                    header = header[:arg.level - 2]
                self.apply_wikitext(arg.title)
                template = None
                templates = arg.title.filter_templates(recursive=False)
                if len(templates) == 1:
                    name = str(templates[0].name).strip()
                    if name in root_header_templates:
                        template = {name: params_to_dict(templates[0].params)}
                        code.remove(templates[0])
                if templates and not template:
                    print(f"{header} {self.word} unrecognized header template in {arg.title}")
                text = str(arg.title).strip()
                if template:
                    if text:
                        print(f"{header} {self.word} has text '{text}' in addition to template {template}")
                        template['text'] = text
                    header.append(template)
                else:
                    header.append(text)
            else:
                self.warn(f"{header} {self.word}: Ha? {typ}  {arg}")

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
            name = str(arg.name).strip()
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
                    self.repl_conditional(arg, code, 1 if key in self.state.templates_no_ns else 2)
                else:
                    raise ValueError(f'Unhandled special {name}')
            else:
                for param in arg.params:
                    self.apply_value(code, param)
                if name in custom_templates:
                    custom_templates[name](self, code, arg)
                elif (name in expand_template and not expand_template[name](arg)) or name in ignore_templates:
                    # self.warn(f"Template {name} should not be expanded")
                    return
                else:
                    template_page = self.state.get_template(name)
                    if template_page:
                        new_text = TemplateParser(
                            f'{self.template_name}.{name}', self.word, template_page.content,
                            params_to_dict(arg.params), self.state).run()
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
