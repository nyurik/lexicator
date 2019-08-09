import re
from dataclasses import dataclass
from typing import Callable

from mwparserfromhell.wikicode import Wikicode

NS_MAIN = 0
NS_USER = 2
NS_USER_TALK = 3
NS_TEMPLATE = 10
NS_TEMPLATE_TALK = 11

RUSSIAN_LANGUAGE = 'Q7737'

HTML_BR_TAGS = {'<br>', '<br >', '<br/>', '<br />'}


@dataclass
class Field:
    name: str
    alt: str = None
    required: bool = True
    parser: Callable[[Wikicode], None] = None


known_fields = [
    # именительный
    Field('Кто/что? (ед)', alt='nom-sg'), Field('nom-sg2', required=False),
    Field('Кто/что? (мн)', alt='nom-pl'), Field('nom-pl2', required=False),
    # родительный
    Field('Нет кого/чего? (ед)', alt='gen-sg'), Field('gen-sg2', required=False),
    Field('Нет кого/чего? (мн)', alt='gen-pl'), Field('gen-pl2', required=False),
    # дательный
    Field('Кому/чему? (ед)', alt='dat-sg'), Field('dat-sg2', required=False),
    Field('Кому/чему? (мн)', alt='dat-pl'), Field('dat-pl2', required=False),
    # винительный
    Field('Кого/что? (ед)', alt='acc-sg'), Field('acc-sg2', required=False),
    Field('Кого/что? (мн)', alt='acc-pl'), Field('acc-pl2', required=False),
    # творительный
    Field('Кем/чем? (ед)', alt='ins-sg'), Field('ins-sg2', required=False),
    Field('Кем/чем? (мн)', alt='ins-pl'), Field('ins-pl2', required=False),
    # предложный
    Field('О ком/чём? (ед)', alt='prp-sg'), Field('prp-sg2', required=False),
    Field('О ком/чём? (мн)', alt='prp-pl'), Field('prp-pl2', required=False),

    Field('loc-sg', required=False),  # словоформа местного падежа
    Field('voc-sg', required=False),  # словоформа звательного падежа
    Field('prt-sg', required=False),  # словоформа разделительного падежа
    Field('Сч', required=False),  # счётная форма
    Field('П', required=False),  # словоформа притяжательного падежа
    Field('Пр', required=False),  # словоформа превратительного падежа

    Field('скл', required=False),
    Field('слоги', required=False),
    Field('кат', required=False),
    Field('зализняк', required=False),
    Field('род', required=False),
    Field('pt', required=False),
    Field('st', required=False),
]

remove_on_st = ['acc-pl', 'dat-pl', 'gen-pl', 'ins-pl', 'nom-pl', 'prp-pl',
                'acc-pl2', 'dat-pl2', 'gen-pl2', 'ins-pl2', 'nom-pl2', 'prp-pl2']

remove_on_pt = ['acc-sg', 'dat-sg', 'gen-sg', 'ins-sg', 'nom-sg', 'prp-sg',
                'acc-sg2', 'dat-sg2', 'gen-sg2', 'ins-sg2', 'nom-sg2', 'prp-sg2']

is_required_fld = {f.alt or f.name: f.required for f in known_fields}

skip_templates = {'сущ ru m a', 'сущ ru f a', 'сущ ru n a', 'сущ ru m ina', 'сущ ru f ina', 'сущ ru n ina',
                  'сущ ru', 'сущ-ru'}

extra_templates = '$|'.join(['падежи', 'кавычки'])
re_template_names = re.compile(
    r'^(([tT]emplate|[шШ]аблон):)?' +
    r'(([iI]nflection )?' +
    r'[сС]ущ[- _]ru' +
    r'($|[ +]$|[ +][^/]*(//)?[^/]*$|/text$|/cat$)|' +
    extra_templates + r'$)')

re_template_name_suspect = re.compile(r'^(([tT]emplate|[шШ]аблон):)?[сС]ущ[ _]')
