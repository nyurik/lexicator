from __future__ import annotations

from typing import Dict, Type, Set, Callable

from lexicator.wikicache import ContentStore, ResolverViaMwParse, LogConfig, MwSite
from .TemplateProcessor import TemplateProcessorBase
from .ru import *


def instantiate(lang_code: str, items: Dict[str, Type]) -> Dict[str, TemplateProcessorBase]:
    return {k: v(lang_code, k) for k, v in items.items()}


templates: Dict[str, Dict[str, TemplateProcessorBase]] = dict(
    ru=instantiate('ru', {
        'transcription-ru': RuTranscription,
        'transcriptions-ru': RuTranscriptions,
        'inflection сущ ru': RuNoun,
        'сущ-ru': RuNoun,
        'сущ ru': RuUnknownNoun,
        'прил': RuAdjective,
        'по-слогам': RuHyphenation,
        '_дореф': RuPreReformSpelling,
        '_прич ru': RuParticiple,
    }),
)

known_headers: Dict[str, Dict[tuple, str]] = dict(
    ru={
        tuple(): 'root',
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
)

handled_types: Dict[str, Set[str]] = dict(
    ru={'noun', 'adjective', 'participle'},
)

resolver_classes: Dict[str, Set[Callable[[LogConfig, MwSite, ContentStore], ResolverViaMwParse]]] = dict(
    ru={RuResolveNoun, RuResolveTranscription, RuResolveTranscriptions},
)
