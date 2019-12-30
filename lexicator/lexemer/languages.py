from __future__ import annotations

from typing import Dict, Type, Set, TYPE_CHECKING

from .ru import RuTranscription, RuTranscriptions, RuNoun, RuUnknownNoun, RuAdjective, RuHyphenation, \
    RuPreReformSpelling, RuParticiple

if TYPE_CHECKING:
    from .TemplateProcessor import TemplateProcessorBase


def instantiate(items: Dict[str, Type]) -> Dict[str, TemplateProcessorBase]:
    return {k: v(k) for k, v in items.items()}


templates: Dict[str, Dict[str, TemplateProcessorBase]] = dict(
    ru=instantiate({
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
