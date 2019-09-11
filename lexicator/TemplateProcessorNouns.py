from lexicator.consts import STRESS_SYMBOLS
from .TemplateUtils import validate_zaliznyak1, validate_asterisk
from .TemplateProcessor import TemplateProcessor
from .Properties import P_GRAMMATICAL_GENDER, P_INFLECTION_CLASS, Q_ZAL_NOUN_CLASSES, \
    zal_normalizations, P_HAS_QUALITY, Q_FEATURES, P_WORD_STEM, ClaimValue, mono_value


class Noun(TemplateProcessor):
    # these params exist in both {{inflection сущ ru}} and {{inflection/ru/noun}}
    common_params = [
        'acc-pl', 'acc-pl2', 'acc-sg', 'acc-sg2', 'case', 'dat-pl', 'dat-pl2', 'dat-sg', 'dat-sg2', 'form', 'gen-pl',
        'gen-pl2', 'gen-sg', 'gen-sg2', 'hide-text', 'ins-pl', 'ins-pl2', 'ins-sg', 'ins-sg2', 'loc-sg', 'nom-pl',
        'nom-pl2', 'nom-sg', 'nom-sg2', 'prp-pl', 'prp-pl2', 'prp-sg', 'prp-sg2', 'prt-sg', 'pt', 'st', 'voc-sg',
        'дореф', 'зализняк', 'зализняк1', 'затрудн', 'зачин', 'кат', 'клитика', 'коммент', 'П', 'Пр', 'род', 'скл',
        'слоги', 'Сч', 'чередование', 'шаблон-кат',
    ]

    # these params are only in {{inflection/ru/noun}}, append them to common
    params2 = common_params + [
        'acc-sg-f', 'dat-sg-f', 'gen-sg-f', 'ins-sg-f', 'nom-sg-f', 'obelus', 'prp-sg-f', 'зализняк-1', 'зализняк-2',
        'фам',
    ]

    def __init__(self, template: str) -> None:
        if template == 'inflection сущ ru':
            params = self.common_params
        elif template == 'сущ-ru':
            params = self.params2
        else:
            raise Exception(f'Unknown template {template}')
        super().__init__(template, params, is_primary=True)

    parameters = {
        #
        # Root claims
        #
        'род': (P_GRAMMATICAL_GENDER, Q_FEATURES, dict(
            м='masculine',
            муж='masculine',
            ж='feminine',
            жен='feminine',
            с='neuter',
            ср='neuter',
            о='common',
            общ='common',
        )),
        'скл': (P_INFLECTION_CLASS, Q_FEATURES, {
            '1': 'declension-1',
            '2': 'declension-2',
            '3': 'declension-3',
            'не': 'indeclinable noun',
            'а': 'adjectival',
            'мс': 'pronoun'
        }),
        'зализняк': (P_INFLECTION_CLASS, Q_ZAL_NOUN_CLASSES, zal_normalizations),
        'зализняк1': validate_zaliznyak1,
        'кат': (P_HAS_QUALITY, Q_FEATURES, dict(
            одуш='animate',
            неодуш='inanimate',
        )),
        # Corresponds to a "*" in 'зализняк', just validate
        'чередование': validate_asterisk,

        #
        # Forms
        #
        # Singular
        'nom-sg': ('form', ('nominative', 'singular'), None),
        'gen-sg': ('form', ('genitive', 'singular'), None),
        'dat-sg': ('form', ('dative', 'singular'), None),
        'acc-sg': ('form', ('accusative', 'singular'), None),
        'ins-sg': ('form', ('instrumental', 'singular'), None),
        'prp-sg': ('form', ('prepositional', 'singular'), None),
        # Uncommon
        'loc-sg': ('form', ('locative', 'singular'), None),
        'voc-sg': ('form', ('vocative', 'singular'), None),
        'prt-sg': ('form', ('partitive', 'singular'), None),
        # Plural
        'nom-pl': ('form', ('nominative', 'plural'), None),
        'gen-pl': ('form', ('genitive', 'plural'), None),
        'dat-pl': ('form', ('dative', 'plural'), None),
        'acc-pl': ('form', ('accusative', 'plural'), None),
        'ins-pl': ('form', ('instrumental', 'plural'), None),
        'prp-pl': ('form', ('prepositional', 'plural'), None),  # Uncommon cases
        # 'Сч':   # счётная форма
        'П': ('form', ('possessive',), None),  # словоформа притяжательного падежа
        # 'Пр':   # словоформа превратительного падежа
        'слоги': None,  # todo: either use the param provided outside of this template, or this one
    }

    def run(self, parser, param_getter):
        parser.primary_form = 'nom-sg'
        self.apply_params(parser, param_getter, self.parameters)

        if 'основа' in parser.unhandled_params:
            P_WORD_STEM.set_claim_on_new(parser.result, ClaimValue(
                mono_value('ru', parser.validate_str(parser.unhandled_params['основа'].replace(STRESS_SYMBOLS, '')))))

    def param_to_form(self, parser, param, param_getter, features):
        super().param_to_form(parser, param, param_getter, features)

        second_form_key = param + '2'
        second_val = param_getter(second_form_key)
        if second_val:
            parser.create_form(second_form_key, second_val, features)


class UnknownNoun(TemplateProcessor):
    def __init__(self, template: str) -> None:
        super().__init__(template, ['2'], is_primary=True)

    def run(self, parser, param_getter):
        pass