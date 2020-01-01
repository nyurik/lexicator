import re
from typing import Dict, Pattern, List, Tuple, Set, Union

from .ru import RUSSIAN_ALPHABET_STRESS, ru_ignore_templates, ru_root_templates, ru_re_template_names
from .uk import uk_root_templates, UKRAINIAN_ALPHABET_STRESS, uk_ignore_templates, uk_re_template_names
from .utils import cleanup_root_templates, double_title_case

NS_TEMPLATE_NAME: Dict[str, str] = dict(
    ru='Шаблон:',
    uk='Шаблон:',
)

# Templates used to indicate the meaning of the word, i.e. meaning 1, meaning 2, ...
MEANING_HEADERS: Dict[str, List[str]] = dict(
    ru=['заголовок', 'з'],  # e.g.  =={{з|I}}==
    uk=['мати'],  # e.g.  == мати I ==
)

Q_LANGUAGE_CODES: Dict[str, str] = dict(
    ru='Q7737',
    uk='Q8798',
)

Q_LANGUAGE_WIKTIONARIES: Dict[str, str] = dict(
    ru='Q22116890',
    uk='Q33109149',
)

Q_SOURCES: Dict[str, Dict[str, str]] = dict(
    ru={
        'оэсря': 'Q67130942',
    },
    uk={},
)

# these types will be
word_types: Dict[str, Dict[str, Pattern]] = dict(
    ru={
        'letters only': re.compile(rf'^[{RUSSIAN_ALPHABET_STRESS}]+$'),
        'multi-word dash-separated': re.compile(rf'^[{RUSSIAN_ALPHABET_STRESS}]+(-[{RUSSIAN_ALPHABET_STRESS}]+)+$'),
        'multi-word space-separated': re.compile(rf'^[{RUSSIAN_ALPHABET_STRESS}]+( [{RUSSIAN_ALPHABET_STRESS}]+)+$'),
    },
    uk={
        'letters only': re.compile(rf'^[{UKRAINIAN_ALPHABET_STRESS}]+$'),
        'multi-word dash-separated': re.compile(rf'^[{UKRAINIAN_ALPHABET_STRESS}]+(-[{UKRAINIAN_ALPHABET_STRESS}]+)+$'),
        'multi-word space-separated': re.compile(
            rf'^[{UKRAINIAN_ALPHABET_STRESS}]+( [{UKRAINIAN_ALPHABET_STRESS}]+)+$'),
    },
)

# Same as root_templates, except it's a list of tuples,
# and first value is a regex instead of a str
template_to_type: Dict[str, List[Tuple[Pattern, Set[str]]]] = dict(
    ru=[
        (re.compile(r'^_прич .*'), {'participle'}),
    ],
    uk=[],
)

# A wiktionary page will only be processed if it has at least one of these strings
wikipage_must_have: Dict[str, Set[str]] = dict(
    ru={'-ru-', '-ru-old-', '-sla-pro-'},  # most common header:  = {{-ru-}} =
    uk={'=uk='},  # most common header:  {{=uk=}}  (without =header= marks)
)

re_section_headers = dict(
    ru=re.compile(r'{{\s*-ru-\s*}}'),
    uk=re.compile(r'{{\s*=uk=\s*}}'),
)

# Templates
ignore_pages_if_template: Dict[str, Set[str]] = dict(
    ru=double_title_case({'к удалению'}),
    uk=double_title_case({}),
)

# Same as ignore_templates, but lists template name prefixes
# noinspection SpellCheckingInspection
re_ignore_template_prefixes: Dict[str, Set[str]] = dict(
    ru={
        'DEFAULTSORT:', 'этимология:', 'родств:', 'гипонимы:', 'синонимы:', '#lst:', 'formatnum:', 'мета:', 'книга:',
        'метаграммы:', 'родств-',
    },
    uk={},
)

# When parsing, whitelist all known but inconsequential templates to catch
# the new useful templates when they are added to Wiktionary.
ignore_templates: Dict[str, set] = dict(
    ru=ru_ignore_templates,
    uk=uk_ignore_templates,
)

# A map of known templates used to extract meaning of the wiktionary page.
# The value indicates part of speech (could be a set if multiple),
# and can be falsy if template does not imply any part of speech.
root_templates: Dict[str, Dict[str, Set[str]]] = dict(
    ru=cleanup_root_templates(ru_root_templates),
    uk=cleanup_root_templates(uk_root_templates),
)

re_template_names: Dict[str, Pattern] = dict(
    ru=ru_re_template_names,
    uk=uk_re_template_names,
)

well_known_parameters: Dict[str, Set[str]] = dict(
    ru={'слоги', 'дореф'},
    uk={},
)

re_allowed_extras: Dict[str, Union[None, Pattern]] = dict(
    ru=re.compile(r'^[и, \n/!]+$'),
    uk=None,
)

known_headers: Dict[str, Dict[tuple, str]] = dict(
    ru={
        ('Морфологические и синтаксические свойства',): 'etymology',
        ('Произношение',): 'pronunciation',
        ('Семантические свойства',): 'semantic',
        ('Семантические свойства', 'Значение',): 'semantic-meaning',
        ('Семантические свойства', 'Синонимы',): 'semantic-synonyms',
        ('Семантические свойства', 'Антонимы',): 'semantic-antonyms',
        ('Семантические свойства', 'Гиперонимы',): 'semantic-hyperonyms',
        ('Семантические свойства', 'Гипонимы',): 'semantic-hyponyms',
        ('Родственные слова',): 'related',
        ('Этимология',): 'etymology',
        ('Фразеологизмы и устойчивые сочетания',): 'phrases',
        ('Перевод',): 'translation',
        ('Библиография',): 'bibliography',
    },
    uk={
        ('Морфологічні та синтаксичні властивості',): 'etymology',
        ('Вимова',): 'pronunciation',
        ('Семантичні властивості',): 'semantic',
        ('Семантические свойства', 'Значення',): 'semantic-meaning',
        ('Семантические свойства', 'Синоніми',): 'semantic-synonyms',
        ('Семантические свойства', 'Антоніми',): 'semantic-antonyms',
        ('Семантические свойства', 'Гіпероніми',): 'semantic-hyperonyms',
        ('Семантические свойства', 'Гіпоніми',): 'semantic-hyponyms',
        ('Семантические свойства', 'Холоніми',): 'semantic-??',
        ('Семантические свойства', 'Мероніми',): 'semantic-??',
        ('Споріднені слова',): 'related',
        # ('Споріднені слова', 'Асоціації',): 'related-??',
        # ('Споріднені слова', 'Переклад',): 'related-??',
        # ('???',): 'etymology',
        ('Усталені та термінологічні словосполучення, фразеологізми',): 'phrases',
        # ('Усталені та термінологічні словосполучення, фразеологізми', 'Прислів\'я та приказки',): 'phrases-??',
        ('Переклад',): 'translation',
        # ('???',): 'bibliography',
    },
)

handled_types: Dict[str, Set[str]] = dict(
    ru={'noun', 'adjective', 'participle'},
    uk={'noun'},
)
