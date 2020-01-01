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
    uk=instantiate('uk', {
    }),
)

resolver_classes: Dict[str, Set[Callable[[LogConfig, MwSite, ContentStore], ResolverViaMwParse]]] = dict(
    ru={RuResolveNoun, RuResolveTranscription, RuResolveTranscriptions},
    uk={},
)
