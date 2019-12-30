from __future__ import annotations

from typing import TYPE_CHECKING

from lexicator.wikicache import ResolverViaMwParse, LogConfig, MwSite

if TYPE_CHECKING:
    from lexicator.wikicache import ContentStore


class ResolveRuNoun(ResolverViaMwParse):
    def __init__(self, log_config: LogConfig, site: MwSite, template_source: ContentStore):
        # noinspection SpellCheckingInspection
        super().__init__(
            site, template_source, log_config=log_config, batch_size=150, template_name='сущ-ru',
            internal_template='inflection/ru/noun', ignore_params=['слоги'],
            output_params=['acc-pl', 'acc-pl2', 'acc-sg', 'acc-sg-f', 'acc-sg2', 'case', 'dat-pl', 'dat-pl2', 'dat-sg',
                           'dat-sg-f', 'dat-sg2', 'form', 'gen-pl', 'gen-pl2', 'gen-sg', 'gen-sg-f', 'gen-sg2',
                           'hide-text', 'ins-pl', 'ins-pl2', 'ins-sg', 'ins-sg-f', 'ins-sg2', 'loc-sg', 'nom-pl',
                           'nom-pl2', 'nom-sg', 'nom-sg-f', 'nom-sg2', 'obelus', 'prp-pl', 'prp-pl2', 'prp-sg',
                           'prp-sg-f', 'prp-sg2', 'prt-sg', 'pt', 'st', 'voc-sg', 'дореф', 'зализняк', 'зализняк-1',
                           'зализняк-2', 'зализняк1', 'затрудн', 'зачин', 'кат', 'клитика', 'коммент', 'П', 'Пр', 'род',
                           'скл', 'слоги', 'Сч', 'фам', 'чередование', 'шаблон-кат'])


class ResolveRuTranscription(ResolverViaMwParse):
    def __init__(self, log_config: LogConfig, site: MwSite, template_source: ContentStore):
        super().__init__(
            site, template_source, log_config=log_config, batch_size=1000,
            template_name='transcription-ru', internal_template='transcription', ignore_params=[],
            output_params=['1', '2', 'lang', 'источник', 'норма'])


class ResolveRuTranscriptions(ResolverViaMwParse):
    def __init__(self, log_config: LogConfig, site: MwSite, template_source: ContentStore):
        super().__init__(
            site, template_source, log_config=log_config, batch_size=500,
            template_name='transcriptions-ru', internal_template='transcriptions', ignore_params=[],
            output_params=['1', '2', '3', '4', 'lang', 'источник', 'мн2', 'норма'])
