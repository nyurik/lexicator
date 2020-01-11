from __future__ import annotations

from html import unescape
from typing import Union, Iterable

from mwparserfromhell import parse as mw_parse
from mwparserfromhell.nodes import Template, Text, Wikilink, Comment, Heading, Argument, Tag, HTMLEntity, \
    ExternalLink, Node
from mwparserfromhell.nodes.extras import Parameter
from mwparserfromhell.wikicode import Wikicode

from .TokenizerState import TokenizerState
from .common import ignore_types, custom_templates


class TemplateParser:
    def __init__(self, template_name: str, word: str, content: str, arguments, state: TokenizerState) -> None:
        self.template_name = template_name
        self.word: str = word
        self.content: str = content
        self.arguments = arguments
        self.state = state

    def run(self) -> Wikicode:
        # print(f'\n------------------ {self.word}: "{self.template_name}" ----------------------')
        code = mw_parse(self.content)
        self.apply_wikitext(code)
        return code

    def parse_page(self):
        code = mw_parse(self.state.page_parser.preparser(self.content))
        for section in code.get_sections(levels=[1],
                                         matches=self.state.page_parser.re_section_headers,
                                         include_headings=False):
            self.state.header = []
            self.parse_section(code, section)

    def parse_section(self, code: Wikicode, section: Wikicode):
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
                if name in self.state.page_parser.ignore_pages_if_template:
                    return None  # ignore these pages

                root_match = self.state.page_parser.re_root_templates_full_str.match(name)
                if root_match or (
                        self.state.page_parser.re_template_names and
                        self.state.page_parser.re_template_names.match(name)):
                    # Remove well-known params
                    for param in list(arg.params):
                        param_name = str(param.name)
                        for re_param in self.state.page_parser.re_well_known_parameters:
                            m = re_param.match(param_name)
                            if not m:
                                continue
                            extras = ''
                            has_templates = False
                            for arg2 in param.value.filter(recursive=False):
                                arg2type = type(arg2)
                                if arg2type == Text:
                                    extras += arg2.value
                                elif arg2type == Template and str(arg2.name) in self.state.page_parser.root_templates:
                                    has_templates = True
                                elif arg2type == Wikilink:
                                    extras += str(arg2.text) if arg2.text else str(arg2.title)
                                elif arg2type != Comment:
                                    raise ValueError(f"cannot parse well known param {str(param).strip()}")
                            extras = extras.strip()
                            if has_templates and extras != '':
                                allowed_extras = self.state.page_parser.re_allowed_extras
                                if not allowed_extras or not allowed_extras.match(extras):
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
                    self.warn(f"{self.state.header} {self.word}: Unknown template {arg}, "
                              f"consider adding it to ignore_templates")
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
                    if name in self.state.page_parser.meaning_headers:
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

    def to_template_name(self, name: str):
        if name.startswith(self.state.page_parser.template_ns) or \
                name.startswith(self.state.page_parser.template_ns_lc):
            return name[len(self.state.page_parser.template_ns):]
        elif name.startswith('Template:') or name.startswith('template:'):
            return name[len('template:'):]
        else:
            return name

    def apply_wikitext(self, code: Wikicode):
        if code:
            # print(str(code).replace('\n', '\\n')[:100])
            for arg in code.filter(recursive=False):
                self.apply_value(code, arg)

    def apply_value(self, code: Wikicode, arg: Union[Node, Template]):
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
                    key = name[len('#ifexist:'):].strip().replace(self.state.page_parser.template_ns, '').strip()
                    self.repl_conditional(arg, code, 1 if key in self.state.page_parser.templates_no_ns else 2)
                else:
                    raise ValueError(f'Unhandled special {name}')
            else:
                for param in arg.params:
                    self.apply_value(code, param)
                if name in custom_templates:
                    custom_templates[name](self, code, arg)
                elif ((name in self.state.page_parser.expand_template
                       and not self.state.page_parser.expand_template[name](arg))
                      or name in self.state.page_parser.ignore_templates):
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

    def repl_conditional(self, arg: Template, code: Wikicode, index: Union[str, int]):
        if arg.has(index):
            param = arg.get(index)
            self.apply_wikitext(param.value)
            code.replace(arg, str(param.value).strip() if param.showkey else param.value)
        else:
            code.remove(arg)

    def warn(self, message: str):
        self.state.warnings.append(message)


def params_to_dict(params: Iterable[Parameter]):
    result = {}
    for p in params:
        value = str(p.value).strip()
        if value:
            result[str(p.name).strip()] = value
    return result
