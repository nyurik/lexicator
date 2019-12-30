import re
from typing import Dict, Pattern, List, Tuple, Set

from lexicator.consts.ru import RUSSIAN_ALPHABET_STRESS, ru_ignore_templates, ru_root_templates, ru_re_template_names
from lexicator.consts.utils import cleanup_root_templates, double_title_case

NS_TEMPLATE_NAME: Dict[str, str] = dict(
    ru='Шаблон:',
)

# Templates used to indicate the meaning of the word, i.e. meaning 1, meaning 2, ...
MEANING_HEADERS: Dict[str, List[str]] = dict(
    ru=['заголовок', 'з'],
)

Q_LANGUAGE_CODES: Dict[str, str] = dict(
    ru='Q7737',
)

Q_LANGUAGE_WIKTIONARIES: Dict[str, str] = dict(
    ru='Q22116890',
)

Q_SOURCES: Dict[str, Dict[str, str]] = dict(
    ru={
        'оэсря': 'Q67130942',
    },
)

# these types will be
word_types: Dict[str, Dict[str, Pattern]] = dict(
    ru={
        'letters only': re.compile(rf'^[{RUSSIAN_ALPHABET_STRESS}]+$'),
        'multi-word dash-separated': re.compile(rf'^[{RUSSIAN_ALPHABET_STRESS}]+(-[{RUSSIAN_ALPHABET_STRESS}]+)+$'),
        'multi-word space-separated': re.compile(rf'^[{RUSSIAN_ALPHABET_STRESS}]+( [{RUSSIAN_ALPHABET_STRESS}]+)+$'),
    },
)

# Same as root_templates, except it's a list of tuples,
# and first value is a regex instead of a str
template_to_type: Dict[str, List[Tuple[Pattern, Set[str]]]] = dict(
    ru=[
        (re.compile(r'^_прич .*'), {'participle'}),
    ],
)

# A wiktionary page will only be processed if it has at least one of these strings
wikipage_must_have: Dict[str, Set[str]] = dict(
    ru={'-sla-pro-', '-ru-', '-ru-old-'},
)

# Templates
ignore_pages_if_template: Dict[str, Set[str]] = dict(
    ru=double_title_case({'к удалению'}),
)

# Same as ignore_templates, but lists template name prefixes
# noinspection SpellCheckingInspection
re_ignore_template_prefixes: Dict[str, Set[str]] = dict(
    ru={
        'DEFAULTSORT:', 'этимология:', 'родств:', 'гипонимы:', 'синонимы:', '#lst:', 'formatnum:', 'мета:', 'книга:',
        'метаграммы:', 'родств-',
    },
)

# When parsing, whitelist all known but inconsequential templates to catch
# the new useful templates when they are added to Wiktionary.
ignore_templates: Dict[str, set] = dict(
    ru=double_title_case(ru_ignore_templates),
)

# A map of known templates used to extract meaning of the wiktionary page.
# The value indicates part of speech (could be a set if multiple),
# and can be falsy if template does not imply any part of speech.
root_templates: Dict[str, Dict[str, Set[str]]] = dict(
    ru=cleanup_root_templates(ru_root_templates),
)

re_template_names: Dict[str, Pattern] = dict(
    ru=ru_re_template_names,
)
