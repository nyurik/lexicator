from .common import NS_TEMPLATE_NAME, MEANING_HEADERS, Q_LANGUAGE_CODES, Q_LANGUAGE_WIKTIONARIES, Q_SOURCES, \
    word_types, template_to_type, wikipage_must_have, ignore_pages_if_template, re_ignore_template_prefixes, \
    ignore_templates, root_templates, re_template_names, re_allowed_extras, re_section_headers, well_known_parameters, \
    known_headers, handled_types
from .consts import re_file, word_types_IPA, NS_MAIN, NS_USER, NS_USER_TALK, NS_TEMPLATE, NS_TEMPLATE_TALK, \
    NS_LEXEME, Q_PART_OF_SPEECH, Q_FEATURES
from .utils import double_title_case, lower_first_letter, upper_first_letter
