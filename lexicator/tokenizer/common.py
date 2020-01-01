from __future__ import annotations

import re
from typing import TYPE_CHECKING, Dict, Callable, Union

from mwparserfromhell.nodes import Template, Text, Tag, Wikilink, HTMLEntity, Comment, ExternalLink, Node
from mwparserfromhell.wikicode import Wikicode

from lexicator.consts import NS_TEMPLATE, re_section_headers

if TYPE_CHECKING:
    from .TemplateParser import TemplateParser

ignore_types = {Text, Tag, Wikilink, Comment, ExternalLink, HTMLEntity}


# noinspection PyUnusedLocal
def flag_template(self: TemplateParser, code: Wikicode, template: Template, flag, index=None):
    if index and template.has(index):
        param = template.get(index)
        self.apply_wikitext(param.value)
        code.replace(template, param)
    else:
        code.remove(template)
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
custom_templates2 = dict(
    ru={
        'прост.': lambda s, c, t: flag_template(s, c, t, 'primitive'),
        'устар.': lambda s, c, t: flag_template(s, c, t, 'outdated'),
        'детск.': lambda s, c, t: flag_template(s, c, t, 'childish'),
        # эта форма слова или ударение является нестандартной для данной схемы словоизменения -- △
        'особ.ф.': lambda s, c, t: flag_template(s, c, t, 'unusual_form', '1'),
        'incorrect': lambda s, c, t: flag_template(s, c, t, 'incorrect', '1'),
    },
    uk={},
)

# Extra language-specific expansion rules
expand_template: Dict[str, Dict[str, Callable[[Node], bool]]] = dict(
    ru={
        'inflection сущ ru': lambda arg: arg.has('form') and str(arg.get('form').value).strip(),
    },
    uk={},
)

preparser_uk = re.compile(rf"^\s*({re_section_headers['uk'].pattern})\s*$", re.MULTILINE)

preparser: Dict[str, Union[None, Callable[[str], str]]] = dict(
    ru=None,
    uk=lambda c: preparser_uk.sub(r"=\1=", c),  # uk uses template to create a header, without the actual header markup
)
