from __future__ import annotations

import re
from typing import TYPE_CHECKING, Dict, Set, Callable, Iterable

from mwparserfromhell.nodes import Template, Text, Tag, Wikilink, HTMLEntity, Comment, ExternalLink, Node
from mwparserfromhell.nodes.extras import Parameter
from mwparserfromhell.wikicode import Wikicode

from lexicator.consts import NS_TEMPLATE

if TYPE_CHECKING:
    from .TemplateParser import TemplateParser

ignore_types = {Text, Tag, Wikilink, Comment, ExternalLink, HTMLEntity}


def params_to_dict(params: Iterable[Parameter]):
    result = {}
    for p in params:
        value = str(p.value).strip()
        if value:
            result[str(p.name).strip()] = value
    return result


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
)

# Extra language-specific expansion rules
expand_template: Dict[str, Dict[str, Callable[[Node], bool]]] = dict(
    ru={
        'inflection сущ ru': lambda arg: arg.has('form') and str(arg.get('form').value).strip(),
    },
)

well_known_parameters: Dict[str, Set[str]] = dict(
    ru={'слоги', 'дореф'},
)

re_allowed_extras = dict(
    ru=re.compile(r'^[и, \n/!]+$'),
)

re_section_headers = dict(
    ru=re.compile(r'{{\s*-ru-\s*}}'),
)
