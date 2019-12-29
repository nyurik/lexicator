import re

from lexicator.consts.utils import cleanup_root_templates, double_title_case
from lexicator.consts.ru import RUSSIAN_ALHABET_STRESS, ru_ignore_templates, ru_root_templates, ru_re_template_names

# Templates used to indicate the meaning of the word, i.e. meaning 1, meaning 2, ...
MEANING_HEADERS = dict(
    ru=['заголовок', 'з'],
)

Q_LANGUAGE_CODES = dict(
    ru='Q7737'
)

Q_LANGUAGE_WIKTIONARIES = dict(
    ru='Q22116890',
)

Q_SOURCES = dict(
    ru={
        'оэсря': 'Q67130942',
    },
)

word_types = dict(
    ru={
        'letters only': re.compile(rf'^[{RUSSIAN_ALHABET_STRESS}]+$'),
        'multi-word dash-separated': re.compile(rf'^[{RUSSIAN_ALHABET_STRESS}]+(-[{RUSSIAN_ALHABET_STRESS}]+)+$'),
        'multi-word space-separated': re.compile(rf'^[{RUSSIAN_ALHABET_STRESS}]+( [{RUSSIAN_ALHABET_STRESS}]+)+$'),
    },
)

# Same as root_templates, except it's a list of tuples,
# and first value is a regex instead of a str
template_to_type = dict(
    ru=[
        (re.compile(r'^_прич .*'), {'participle'}),
    ]
)

# A wiktionary page will only be processed if it has at least one of these strings
wikipage_must_have = dict(
    ru={'-sla-pro-', '-ru-', '-ru-old-'},
)

# Templates
ignore_pages_if_template = dict(
    ru=double_title_case({'к удалению'}),
)

# Same as ignore_templates, but lists template name prefixes
# noinspection SpellCheckingInspection
re_ignore_template_prefixes = dict(
    ru={
        'DEFAULTSORT:', 'этимология:', 'родств:', 'гипонимы:', 'синонимы:', '#lst:', 'formatnum:', 'мета:', 'книга:',
        'метаграммы:', 'родств-',
    },
)

# When parsing, whitelist all known but inconsequential templates to catch
# the new useful templates when they are added to Wiktionary.
ignore_templates = dict(
    ru=ru_ignore_templates,
)

# A map of known templates used to extract meaning of the wiktionary page.
# The value indicates part of speech (could be a set if multiple),
# and can be falsy if template does not imply any part of speech.
root_templates = dict(
    ru=cleanup_root_templates(ru_root_templates)
)

re_template_names = dict(
    ru=ru_re_template_names,
)
