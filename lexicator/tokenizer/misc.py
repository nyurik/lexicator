from __future__ import annotations

import re
from typing import TYPE_CHECKING

from mwparserfromhell.nodes import Template, Text, Tag, Wikilink, HTMLEntity, Comment, ExternalLink

from lexicator.consts import root_templates, NS_TEMPLATE

if TYPE_CHECKING:
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
