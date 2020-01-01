import re

import unicodedata

STRESS_SYMBOL_PRI = '\u0301'
STRESS_SYMBOL_SEC = '\u0300'

UKRAINIAN_ALPHABET = 'аАбБвВгГґҐдДеЕєЄжЖзЗиИіІїЇйЙкКлЛмМнНоОпПрРсСтТуУфФхХцЦчЧшШщЩьЬюЮяЯ'

UKRAINIAN_STRESSABLE_LETTERS = 'аАеЕєЄиИіІїЇоОуУюЮяЯ'
UKRAINIAN_ALPHABET_STRESS = \
    UKRAINIAN_ALPHABET + STRESS_SYMBOL_PRI + STRESS_SYMBOL_SEC + unicodedata.normalize(
        'NFC',
        ''.join(((v + STRESS_SYMBOL_PRI + v + STRESS_SYMBOL_SEC) for v in UKRAINIAN_STRESSABLE_LETTERS)))


def remove_stress(word: str) -> str:
    return unicodedata.normalize(
        'NFC', unicodedata.normalize('NFD', word).replace(STRESS_SYMBOL_PRI, '').replace(STRESS_SYMBOL_SEC, ''))


# noinspection SpellCheckingInspection
uk_ignore_templates = {
}

# noinspection SpellCheckingInspection
uk_root_templates = {
    'імен uk': 'noun',
    'inflection імен uk': 'noun',
    'морфо-uk': 0,
    'audio': 0,
}

# noinspection SpellCheckingInspection
uk_re_template_names = re.compile(
    r'^(([tT]emplate|[шШ]аблон):)?' + r'('
                                      r'імен uk '
                                      r')'
)

Q_ZAL_ADJ_CLASSES = {
}

Q_ZAL_NOUN_CLASSES = {
}
