import dataclasses
from dataclasses import dataclass
from typing import Set

from mwparserfromhell import parse as mw_parse
from mwparserfromhell.nodes import Argument, Template, Text, Tag, Wikilink, Heading
from mwparserfromhell.nodes.extras import Parameter

from .consts import known_fields
from .utils import extract_template_params
from .WikiPages import WikiPage, root_templates


@dataclass
class SpecialTemplate:
    flag: str
    action: str


# noinspection PyUnusedLocal
def syllables(self: 'TemplateParser', code, template: Template):
    # ‧.‧  mean no break because there is only one character on either side
    code.replace(template, '‧'.join([str(v) for v in template.params if not v.showkey]).replace('‧.‧', ''))


# noinspection PyUnusedLocal
def syllables2(self: 'TemplateParser', code, template: Template):
    if template.has('1'):
        code.replace(template, '‧'.join(str(template.get('1').value).split('/')))
    else:
        self.warn(f'Unable to find param1 in {template}')


# noinspection PyUnusedLocal
def flag_template(self: 'TemplateParser', code, template: Template, flag, index=None):
    if index and template.has(index):
        param = template.get(index)
        self.apply_wikitext(param.value)
        code.replace(template, param)
    else:
        code.remove(template)
    if self.parser.flags is None:
        self.parser.flags = set()
    self.parser.flags.add(flag)


custom_templates = {
    'по-слогам': syllables,
    'по слогам': syllables,
    'слоги': syllables2,
    '-': lambda s, c, t: c.replace(t, '\u00a0— '),
    'PAGENAME': lambda s, c, t: c.replace(t, s.word),
    'NAMESPACE': lambda s, c, t: c.replace(t, ''),
    'ns:0': lambda s, c, t: c.replace(t, ''),
}

custom_templates2 = {
    'прост.': lambda s, c, t: flag_template(s, c, t, 'primitive'),
    'устар.': lambda s, c, t: flag_template(s, c, t, 'outdated'),
    'детск.': lambda s, c, t: flag_template(s, c, t, 'childish'),
    # эта форма слова или ударение является нестандартной для данной схемы словоизменения -- △
    'особ.ф.': lambda s, c, t: flag_template(s, c, t, 'unusual_form', '1'),
    'incorrect': lambda s, c, t: flag_template(s, c, t, 'incorrect', '1'),
}


class Parser:
    def __init__(self,
                 templates,
                 existing_entities,
                 fields: Set[str] = None):
        self.templates = templates
        self.existing_entities = existing_entities
        self.fields = [v for v in known_fields if v.name in fields] if fields else known_fields
        self.expand_template = {
            'inflection сущ ru': lambda args: args.has('form') and not str(args.get('form').value).strip(),
            'падежи': lambda args: False,
            'сущ-ru': lambda args: False,
        }
        assert (set(root_templates) < set(self.expand_template.keys()))

    def parse_word(self, word: WikiPage):
        return WordParser(word, self).run()


class WordParser:

    def __init__(self, word: WikiPage, parser: Parser) -> None:
        self.flags = None
        self.word = word
        self.warnings = []
        self.templates = parser.templates
        self.expand_template = parser.expand_template

    def run(self):
        results = []
        for idx, template in enumerate(self.word.templates):
            wikitext = str(Template(template[0], params=[Parameter(k, v) for k, v in template[1].items()]))
            code = TemplateParser('', self.word.title, wikitext, {}, self).run()
            for t_name, params in extract_template_params(code):
                if params is not None:
                    params = {k: v for k, v in params.items() if v}
                    if self.warnings:
                        self.warnings.insert(0, "WARNINGS")
                        val = (t_name, params, self.warnings)
                        self.warnings = []
                    else:
                        val = (t_name, params)
                    if val not in results:
                        results.append(val)
        return dataclasses.replace(self.word, templates=results)


class TemplateParser:

    def __init__(self, template_name: str, word: str, content, arguments, parser: WordParser,
                 disable_warnings=False) -> None:
        self.template_name = template_name
        self.word = word
        self.content = content
        self.arguments = arguments
        self.parser = parser
        self.disable_warnings = disable_warnings

    def run(self):
        # print(f'\n------------------ {self.word}: "{self.template_name}" ----------------------')
        code = mw_parse(self.content)
        self.apply_wikitext(code)
        return code

    def apply_wikitext(self, code):
        if code:
            # print(str(code).replace('\n', '\\n')[:100])
            for arg in code.filter(recursive=False):
                self.apply_value(code, arg)

    def apply_value(self, code, arg):
        typ = type(arg)
        if typ == Text:
            pass
        elif typ == Argument:
            self.apply_wikitext(arg.name)
            arg_name = str(arg.name)
            if arg_name in self.arguments:
                code.replace(arg, self.arguments[arg_name])
            elif arg.default is not None:
                self.apply_wikitext(arg.default)
                code.replace(arg, arg.default)
        elif typ == Template:
            self.apply_wikitext(arg.name)
            name = str(arg.name.get(0)).strip()
            if name == '#if:':
                self.repl_conditional(
                    arg, code, 2 if len(arg.name.nodes) == 1 or arg.name.get(1).strip() == '' else 1)
            elif name == '#ifeq:':
                if not arg.has('1'):
                    code.remove(arg)
                else:
                    if len(arg.name.nodes) == 1:
                        val1 = ''
                    else:
                        val1 = arg.name.get(1).strip()
                    val2 = arg.get('1')
                    self.apply_wikitext(val2.value)
                    val2 = str(val2.value).strip()
                    self.repl_conditional(arg, code, 3 if val1 == val2 else 2)
            elif name == '#switch:':
                key = str(arg.name)[len('#switch:'):]
                if not arg.has(key):
                    key = '#default'
                    if not arg.has(key):
                        key = '1'
                        if not arg.has(key):
                            self.warn(f'switch value "{key}" not found in {arg}')
                self.repl_conditional(arg, code, key)
            elif name.startswith('#ifexist:'):
                key = str(arg.name).replace('#ifexist:', '').strip().replace('Шаблон:', '').strip()
                self.repl_conditional(arg, code, 1 if key in self.parser.templates else 2)
            else:
                unexpandable = name in self.parser.expand_template and not self.parser.expand_template[name](arg)
                old_warnings = self.disable_warnings
                if unexpandable:
                    self.disable_warnings = True
                for param in arg.params:
                    self.apply_value(code, param)
                self.disable_warnings = old_warnings

                if name in custom_templates:
                    custom_templates[name](self, code, arg)
                elif unexpandable:
                    # self.warn(f"Template {name} should not be expanded")
                    pass
                elif name in self.parser.templates:
                    sub_params = {str(p.name): str(p.value) for p in arg.params}
                    new_text = TemplateParser(
                        f'{self.template_name}.{name}', self.word, self.parser.templates[name].content,
                        sub_params, self.parser, self.disable_warnings).run()
                    code.replace(arg, str(new_text).strip())
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
        if not self.disable_warnings:
            self.parser.warnings.append(message)
