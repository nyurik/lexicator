import re

from lexicator.consts import Q_FEATURES
from lexicator.consts.ru import Q_ZAL_ADJ_CLASSES
from lexicator.lexemer import TemplateProcessor, normalize_zal
from lexicator.lexemer.Properties import P_INFLECTION_CLASS, P_HAS_QUALITY


def validate_flag(params_to_check, enable=False):
    # noinspection PyUnusedLocal
    def validate(processor, parser, value, param, param_getter, params):
        for param in params_to_check:
            val = param_getter(param, False)
            if (val is None) == enable:
                if enable:
                    raise ValueError(f'Value {param} is expected but not given')
                else:
                    raise ValueError(f'Value {param}={val} is not expected')

    return validate


class RuAdjective(TemplateProcessor):
    def __init__(self, template: str) -> None:
        super().__init__(template, [
            'acc-pl-a', 'acc-pl-n', 'acc-sg-f', 'acc-sg-m-a', 'acc-sg-m-n', 'acc-sg-n', 'anim', 'dat-pl', 'dat-sg-f',
            'dat-sg-m', 'dat-sg-n', 'gen-pl', 'gen-sg-f', 'gen-sg-m', 'gen-sg-n', 'ins-pl', 'ins-sg-f', 'ins-sg-m',
            'ins-sg-n', 'nof', 'nol', 'nom', 'nom-pl', 'nom-sg-f', 'nom-sg-m', 'nom-sg-n', 'non', 'nowrap', 'prp-pl',
            'prp-sg-f', 'prp-sg-m', 'prp-sg-n', 'srt-pl', 'srt-sg-f', 'srt-sg-m', 'srt-sg-n', 'краткая', 'суфф'
        ], is_primary=True)

    parameters = {
        #
        # Forms
        #
        # Singular masculine
        'nom-sg-m': ('form', ('nominative', 'singular', 'masculine'), None),
        'gen-sg-m': ('form', ('genitive', 'singular', 'masculine'), None),
        'dat-sg-m': ('form', ('dative', 'singular', 'masculine'), None),
        'acc-sg-m-a': ('form', ('accusative', 'animate', 'singular', 'masculine'), None),
        'acc-sg-m-n': ('form', ('accusative', 'inanimate', 'singular', 'masculine'), None),
        'ins-sg-m': ('form', ('instrumental', 'singular', 'masculine'), None),
        'prp-sg-m': ('form', ('prepositional', 'singular', 'masculine'), None),
        'srt-sg-m': ('form', ('short-form-adjective', 'singular', 'masculine'), None),
        # Singular Neuter
        'nom-sg-n': ('form', ('nominative', 'singular', 'neuter'), None),
        'gen-sg-n': ('form', ('genitive', 'singular', 'neuter'), None),
        'dat-sg-n': ('form', ('dative', 'singular', 'neuter'), None),
        'acc-sg-n': ('form', ('accusative', 'singular', 'neuter'), None),
        'ins-sg-n': ('form', ('instrumental', 'singular', 'neuter'), None),
        'prp-sg-n': ('form', ('prepositional', 'singular', 'neuter'), None),
        'srt-sg-n': ('form', ('short-form-adjective', 'singular', 'neuter'), None),
        # Singular feminine
        'nom-sg-f': ('form', ('nominative', 'singular', 'feminine'), None),
        'gen-sg-f': ('form', ('genitive', 'singular', 'feminine'), None),
        'dat-sg-f': ('form', ('dative', 'singular', 'feminine'), None),
        'acc-sg-f': ('form', ('accusative', 'singular', 'feminine'), None),
        'ins-sg-f': ('form', ('instrumental', 'singular', 'feminine'), None),
        'prp-sg-f': ('form', ('prepositional', 'singular', 'feminine'), None),
        'srt-sg-f': ('form', ('short-form-adjective', 'singular', 'feminine'), None),
        # Plural
        'nom-pl': ('form', ('nominative', 'plural'), None),
        'gen-pl': ('form', ('genitive', 'plural'), None),
        'dat-pl': ('form', ('dative', 'plural'), None),
        'acc-pl-a': ('form', ('accusative', 'animate', 'plural'), None),
        'acc-pl-n': ('form', ('accusative', 'inanimate', 'plural'), None),
        'ins-pl': ('form', ('instrumental', 'plural'), None),
        'prp-pl': ('form', ('prepositional', 'plural'), None),
        'srt-pl': ('form', ('short-form-adjective', 'plural'), None),

        # Flags to enable/disables sections
        'краткая': validate_flag([  # If set, enables srt-*
            'srt-pl', 'srt-sg-f', 'srt-sg-m', 'srt-sg-n'], enable=True),
        'anim': validate_flag([  # Disables multiple accusative forms
            'acc-sg-m-n', 'acc-pl-n']),
        'nof': validate_flag([  # Disables feminine
            'nom-sg-f', 'gen-sg-f', 'dat-sg-f', 'acc-sg-f', 'ins-sg-f', 'prp-sg-f', 'srt-sg-f']),
        'non': validate_flag([  # Disables neuter
            'nom-sg-n', 'gen-sg-n', 'dat-sg-n', 'acc-sg-n', 'ins-sg-n', 'prp-sg-n', 'srt-sg-n']),
        'nom': validate_flag([  # Disables masculine
            'nom-sg-m', 'gen-sg-m', 'dat-sg-m', 'acc-sg-m-a', 'acc-sg-m-n', 'ins-sg-m', 'prp-sg-m', 'srt-sg-m']),
        'nol': validate_flag([  # Disables plural
            'nom-pl', 'gen-pl', 'dat-pl', 'acc-pl-a', 'acc-pl-n', 'ins-pl', 'prp-pl', 'srt-pl']),

        'nowrap': None,  # ignore CSS
        # 'суфф': '',  # if set, this text is added to all forms (probably HTML, so error out)
    }

    re_zel_parser = re.compile(r'^_прил ru ([0-9][a-z]?)$')

    def run(self, parser, param_getter, params: dict):
        z_type = None
        adj_type = None
        adj_rank = None
        for header, template, params in parser.data_section:
            if header != 'etymology':
                continue
            m = self.re_zel_parser.match(template)
            if not m:
                continue
            if z_type:
                raise ValueError('Multiple adj found')
            z_type = m.group(1)
            # качественное, относительное, притяжательное
            adj_type = params['тип'] if 'тип' in params else None
            adj_rank = params['степень'] if 'степень' in params else None

        if z_type:
            self.create_claim(parser, '', z_type, P_INFLECTION_CLASS, Q_ZAL_ADJ_CLASSES, normalize_zal)
        else:
            raise ValueError('unable to find adjective Z type')
        if adj_type:
            raise ValueError(f"not implemented: тип={adj_type} is set but not used by the adjective processor")
        if adj_rank:
            raise ValueError(f"not implemented: степень={adj_rank} is set but not used by the adjective processor")

        self.apply_params(parser, param_getter, self.parameters, params)
        parser.primary_form = 'nom-sg-m'
        parser.add_stem()

    def param_to_form(self, parser, param, param_getter, features) -> None:
        param_value = param_getter(param)
        if param != 'ins-sg-f' or ' ' not in param_value:
            return super(RuAdjective, self).param_to_form(parser, param, param_getter, features)

        words = parser.split_words(param_value, 2)
        parser.create_form(param, words[0], features)
        parser.create_form(param + '2', words[1], features)


class RuParticiple(TemplateProcessor):
    def __init__(self, template: str) -> None:
        # noinspection SpellCheckingInspection
        super().__init__(
            template,
            ['hide-text', 'nocat', 'вид', 'время', 'дореф', 'залог', 'коммент', 'склонение', 'склонение', 'слоги',
             'соотв', 'соотв-мн', ], is_primary=False)

    parameters = {
        'время': (P_HAS_QUALITY, Q_FEATURES, dict(
            прош='past tense',  # прошедшего времени
            наст='present tense',  # настоящего времени
            буд='future tense',  # настоящего времени
        )),

        'вид': (P_HAS_QUALITY, Q_FEATURES, dict(
            несов='imperfective aspect',  # несовершенный вид
            н='imperfective aspect',
            сов='perfective aspect',  # совершенный вид
            с='perfective aspect',
        )),

        'залог': (P_HAS_QUALITY, Q_FEATURES, dict(
            действ='active voice',  # действительный залог
            страд='passive voice',  # страдательный залог
            возвр='reflexive voice',  # возвратный залог
        )),

        'склонение': (P_INFLECTION_CLASS, Q_ZAL_ADJ_CLASSES, normalize_zal),
    }

    def run(self, parser, param_getter, params: dict):
        self.apply_params(parser, param_getter, self.parameters, params)
