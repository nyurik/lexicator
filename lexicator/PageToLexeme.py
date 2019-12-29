from typing import List

from lexicator.Properties import *
from lexicator.ResolverViaMwParse import json_key
from lexicator.TemplateProcessor import TemplateProcessorBase
from lexicator.TemplateProcessorAdjective import Adjective, Participle
from lexicator.TemplateProcessorCommon import TranscriptionRu, TranscriptionsRu, PreReformSpelling, Hyphenation
from lexicator.TemplateProcessorNouns import Noun, UnknownNoun
from lexicator.TemplateUtils import test_str
from lexicator.consts import root_templates, word_types, template_to_type, re_file, word_types_IPA
from lexicator.utils import remove_stress


class PageToLexeme:

    def __init__(self, title, data_section, resolvers: Dict[str, 'ContentStore']) -> None:
        self.title = title
        self.data_section = data_section
        self.resolvers = resolvers
        self.word_type: str = None
        self.grammar_types = set()

    def run(self) -> Any:
        self.word_type = self.calc_word_type()
        one_lexeme = LexemeParserState(self, self.data_section)
        if one_lexeme.grammar_type in self.grammar_types:
            raise ValueError(f'More than one {one_lexeme.grammar_type} found')
        self.grammar_types.add(one_lexeme.grammar_type)

        result = one_lexeme.create_lexeme()

        if not result:
            raise ValueError('No lexemes found')
        return result

    def calc_word_type(self):
        for word_type, regex in word_types.items():
            if regex.match(self.title):
                return word_type
        raise ValueError('Unrecognized word type')

    def validate_str(self, val, param):
        if not word_types[self.word_type].match(test_str(val, param)):
            raise ValueError(f'word {val} does not match the expected word type "{self.word_type}"')
        return val


known_headers = {
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
}


def data_section_sorter(values):
    header, template, params = values
    return 0 if template not in templates else 1 if templates[template].is_primary else 2


def set_imported_from_wkt(data):
    if 'claims' in data:
        for props in data['claims'].values():
            for claim in props:
                set_refernces_on_new(claim, {P_IMPORTED_FROM_WM: Q_RU_WIKTIONARY})


class LexemeParserState:

    def __init__(self, parent: PageToLexeme, data_section):
        self.parent = parent
        self.title = parent.title
        self.data_section = data_section
        self.unhandled_params = {}
        self.form_by_param = {}
        self.grammar_type: str = None
        self.primary_form: str = None
        self.result: dict = None
        self.processed = False

        self.grammar_type = self.get_grammar_type()
        self.extras = {}

    @property
    def primary_form(self):
        if self.__primary_form is None:
            raise ValueError('primary_form was never set')
        return self.__primary_form

    @primary_form.setter
    def primary_form(self, primary_form):
        self.__primary_form = primary_form

    def create_lexeme(self):
        try:
            lex_category = Q_PART_OF_SPEECH[self.grammar_type]
        except KeyError:
            raise ValueError(f"Unhandled lexical category '{self.grammar_type}'")

        self.result = dict(
            lemmas=dict(ru=dict(language='ru', value=self.title)),
            lexicalCategory=lex_category,
            language=Q_RUSSIAN_LANG,
        )

        try:
            self.data_section = sorted(
                [(known_headers[tuple(h[1:])], t, p) for h, t, p in self.data_section],
                key=data_section_sorter)
        except KeyError as err:
            raise ValueError(f"unknown section header {err} found")

        for header, template, params in self.data_section:
            if template not in templates or not templates[template].autorun:
                self.unhandled_params.update(params)
            else:
                self.run_template(template, params)

        set_imported_from_wkt(self.result)
        for typ in ['senses', 'forms']:
            if typ in self.result:
                for val in self.result[typ]:
                    set_imported_from_wkt(val)

        return self.result

    def get_grammar_type(self):
        grammar_type: Set = None

        def add_types(typ):
            if typ:
                nonlocal grammar_type
                if grammar_type is None:
                    grammar_type = typ.copy()
                else:
                    grammar_type.intersection_update(typ)

        for header, template, params in self.data_section:
            if template in root_templates:
                add_types(root_templates[template])
            else:
                for rx, typ in template_to_type:
                    if rx.match(template):
                        add_types(typ)
        if not grammar_type:
            raise ValueError(f"Unknown grammar type:\n{self.data_section}")
        if len(grammar_type) > 1:
            if grammar_type == root_templates['прил']:
                return 'adjective'
            raise ValueError(
                f"Multiple types found in {self.title} - {', '.join(grammar_type)}:\n{self.data_section}")
        return grammar_type.pop()

    def validate_str(self, val, param):
        return self.parent.validate_str(val, param)

    @staticmethod
    def validate_file(val):
        if not re_file.match(val):
            raise ValueError(f'File {val} does not appear to be correct')
        return val

    def validate_ipa(self, val):
        if not word_types_IPA[self.parent.word_type].match(val):
            raise ValueError(f'IPA {val} for {self.parent.word_type} does not appear to be correct')
        return val

    def get_extra_state(self, template):
        try:
            return self.extras[template]
        except KeyError:
            self.extras[template] = {}
            return self.extras[template]

    def set_pronunciation_qualifier(self, index, form_id, prop, param_value, validator):
        if param_value:
            pron = self.get_pronunciation(form_id, index)
            set_qualifiers_on_new(pron, {prop: validator(param_value)})

    def set_pronunciation_reference(self, index, form_id, param_value):
        if param_value:
            pron = self.get_pronunciation(form_id, index)
            try:
                refs = {P_DESCRIBED_BY: Q_SOURCES[param_value]}
            except KeyError:
                raise ValueError(f"unable to set pronunciation reference: {param_value} not found in Q_SOURCES")
            set_refernces_on_new(pron, refs)

    def get_pronunciation(self, form_id, index):
        if form_id not in self.form_by_param:
            raise ValueError(f"form {form_id} does not exist")
        form = self.form_by_param[form_id]
        try:
            pronunciations = form['claims'][P_PRONUNCIATION.id]
        except KeyError:
            pronunciations = []
            if 'claims' not in form:
                form['claims'] = {}
            form['claims'][P_PRONUNCIATION.id] = pronunciations
        if index >= len(pronunciations):
            if not pronunciations:
                word = form['representations']['ru']['value']
            else:
                word = P_PRONUNCIATION.get_value(pronunciations[0])['text']
            self.add_pronunciation(form, word)
        return pronunciations[index]

    def set_val(self, param_value, prop: Property, form):
        if param_value:
            if form not in self.form_by_param:
                raise ValueError(f"form {form} does not exist, trying to set {prop}={param_value}")
            if isinstance(param_value, str):
                param_value = ClaimValue(test_str(param_value, prop.name))
            prop.set_claim_on_new(self.form_by_param[form], param_value)

    def create_form(self, form_name, word, features: List[str]):
        if 'forms' not in self.result:
            self.result['forms'] = []
        stressless_word = remove_stress(word)
        form = dict(
            add='',  # without this forms are not added
            representations=dict(
                ru=dict(language='ru', value=self.validate_str(stressless_word, 'form_representation'))
            ),
            grammaticalFeatures=[Q_FEATURES[v] for v in features],
        )
        if stressless_word != word:
            self.add_pronunciation(form, word)
        self.result['forms'].append(form)
        self.form_by_param[form_name] = form

    def add_pronunciation(self, form, word):
        P_PRONUNCIATION.set_claim_on_new(form, ClaimValue(
            mono_value('ru', self.validate_str(word, P_PRONUNCIATION.name))))

    def resolve_lua(self, template, params):
        if template in self.parent.resolvers:
            return self.parent.resolvers[template].get(json_key(template, params)).data
        return params

    def split_words(self, param_value, count_expected=None):
        if self.parent.word_type == 'multi-word space-separated':
            raise ValueError(f"Not implemented word type '{self.parent.word_type}'")
        words = param_value.split(' ')
        if count_expected and len(words) != count_expected:
            raise ValueError(f'Unexpected number of words, should be {count_expected} - {words}')
        return words

    def run_template(self, template, params):
        templates[template].process(self, params)

    def add_stem(self):
        if 'основа' in self.unhandled_params:
            P_WORD_STEM.set_claim_on_new(self.result, ClaimValue(
                mono_value('ru', self.validate_str(remove_stress(self.unhandled_params['основа']), 'основа'))))


templates: Dict[str, TemplateProcessorBase] = {k: v(k) for k, v in {
    'transcription-ru': TranscriptionRu,
    'transcriptions-ru': TranscriptionsRu,
    'inflection сущ ru': Noun,
    'сущ-ru': Noun,
    'сущ ru': UnknownNoun,
    'прил': Adjective,
    'по-слогам': Hyphenation,
    '_дореф': PreReformSpelling,
    '_прич ru': Participle,
}.items()}
