from typing import List

from lexicator.LuaExecutor import json_key
from lexicator.Properties import *


def ru_mono(v):
    return mono_value('ru', v)


def create_form(word, features: List[str]) -> dict:
    return dict(
        add='',  # without this forms are not added
        representations=dict(
            ru=dict(language='ru', value=word)
        ),
        grammaticalFeatures=features,
    )


class LexemeTemplateParser:
    def __init__(self, page, resolve_noun_ru, resolve_transcriptions_ru) -> None:
        self.page = page
        self.resolve_noun_ru = resolve_noun_ru
        self.resolve_transcriptions_ru = resolve_transcriptions_ru
        self.form_by_param = {}

        self.result = dict(
            lemmas=dict(
                ru=dict(language='ru', value=self.page.title)
            ),
            language=Q_RUSSIAN_LANG,
        )
        self.processed = False

    def run(self):
        for header, templ, params in self.page.data:
            if templ in templates:
                runner = templates[templ](self)
                runner.run(params)
                if self.result is None:
                    break
        return self.result


class TranscriptionsRu:
    def __init__(self, parser: LexemeTemplateParser) -> None:
        self.parser = parser

    def run(self, params):
        if 'forms' not in self.parser.result:
            raise ValueError('data.forms exists')

        vals = self.parser.resolve_transcriptions_ru.get(json_key('transcriptions-ru', params)).data

        self.set_val(vals, '3', P_PRONUNCIATION_AUDIO, 'nom-sg')
        self.set_val(vals, '4', P_PRONUNCIATION_AUDIO, 'nom-pl')
        self.set_val(vals, '1', P_IPA_TRANSCRIPTION, 'nom-sg')
        self.set_val(vals, '2', P_IPA_TRANSCRIPTION, 'nom-pl')
        self.set_val(vals, 'мн2', P_IPA_TRANSCRIPTION, 'nom-pl2')

    def set_val(self, values, val, prop, form):
        if val in values:
            prop.set_claim_on_new(self.parser.form_by_param[form], ClaimValue(values[val]))


class InflectionNoun:
    def __init__(self, parser: LexemeTemplateParser) -> None:
        self.parser = parser

    parameters = {
        #
        # Root claims
        #
        'род': (P_GRAMMATICAL_GENDER, Q_GENDERS, dict(
            м='masculine',
            муж='masculine',
            ж='feminine',
            жен='feminine',
            с='neuter',
            ср='neuter',
            о='common',
            общ='common',
        )),
        'скл': (P_INFLECTION_CLASS, Q_DECLENSIONS, dict(
            не='indeclinable noun',
            а='adjectival',
            мс='pronoun',
        )),
        'зализняк': (P_INFLECTION_CLASS, Q_ZEL_CLASSES, None),
        'кат': (P_HAS_QUALITY, Q_QUALITIES, dict(
            одуш='animate',
            неодуш='inanimate',
        )),

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
        'prp-pl': ('form', ('prepositional', 'plural'), None),        # Uncommon cases
        # 'Сч':   # счётная форма
        'П': ('form', ('possessive',), None),  # словоформа притяжательного падежа
        # 'Пр':   # словоформа превратительного падежа
    }

    def run(self, params):
        if 'forms' in self.parser.result:
            raise ValueError('data.forms already exists')

        forms = None
        done_params = set()
        self.parser.result['lexicalCategory'] = Q_PART_OF_SPEECH['noun']

        for param in self.parameters:
            if param not in params:
                continue
            prop, q_map, param_map = self.parameters[param]
            if isinstance(prop, Property):
                val = params[param]
                val = param_map[val] if param_map and val in param_map else val
                if val not in q_map:
                    raise ValueError(f"Unknown parameter value {param}={val}")
                prop.set_claim_on_new(self.parser.result, ClaimValue(q_map[val]))
            elif prop == 'form':
                if forms is None:
                    forms = []
                    self.parser.result['forms'] = forms

                features = [Q_FEATURES[v] for v in q_map]
                form = create_form(params[param], features)
                forms.append(form)
                self.parser.form_by_param[param] = form

                add_hyphenation = param == 'nom-sg' and 'слоги' in params
                if add_hyphenation:
                    P_HYPHENATION.set_claim_on_new(form, ClaimValue(params['слоги']))
                    done_params.add('слоги')

                second_form_key = param + '2'
                if second_form_key in params:
                    form = create_form(params[second_form_key], features)
                    forms.append(form)
                    self.parser.form_by_param[second_form_key] = form
                    done_params.add(second_form_key)
                    if add_hyphenation:
                        print(f"Word {self.parser.page.title} has two 'nom-sg' forms, skipping second hyphenation")
            else:
                raise KeyError()

            done_params.add(param)

        unprocessed_params = set(params.keys()) - done_params
        if unprocessed_params:
            print(f"Unrecognized parameters:\n" + '\n'.join((f'* {k}={params[k]}' for k in unprocessed_params)))
            self.parser.result = None


templates = {
    'transcriptions-ru': TranscriptionsRu,
    'inflection сущ ru': InflectionNoun,
}
