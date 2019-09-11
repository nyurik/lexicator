import dataclasses

from .Properties import *
from .ResolverViaMwParse import json_key
from .TemplateProcessor import TemplateProcessorBase
from .TemplateProcessorAdjective import Adjective
from .TemplateProcessorCommon import TranscriptionRu, TranscriptionsRu, PreReformSpelling, \
    Hyphenation
from .TemplateProcessorNouns import Noun, UnknownNoun
from .TemplateUtils import test_str
from .consts import root_templates, word_types, template_to_type, STRESS_SYMBOLS, re_file, re_IPA_str
from .utils import PageContent, list_to_dict_of_lists


class PageToLexeme:

    def __init__(self, page, resolvers: Dict[str, 'ContentStore']) -> None:
        self.page = page
        self.title = page.title
        self.resolvers = resolvers
        self.word_type: str = None
        self.grammar_types = set()

    def run(self) -> PageContent:
        self.word_type = self.calc_word_type()
        results = []
        sections = list_to_dict_of_lists(self.page.data, key=lambda v: v[0][0] if v[0] and v[0][0] is not None else '')
        for data_section in sections.values():
            one_lexeme = LexemeParserState(self, data_section)
            if one_lexeme.grammar_type in self.grammar_types:
                raise ValueError(f'More than one {one_lexeme.grammar_type} found')
            self.grammar_types.add(one_lexeme.grammar_type)
            lex = one_lexeme.create_lexeme()
            if lex:
                results.append(lex)

        if not results:
            raise ValueError('No lexemes found')
        return dataclasses.replace(self.page, data=results, content=None)

    def calc_word_type(self):
        for word_type, regex in word_types.items():
            if regex.match(self.title):
                return word_type
        raise ValueError('Unrecognized word type')

    def validate_str(self, val):
        if not word_types[self.word_type].match(test_str(val)):
            raise ValueError(f'word {val} does not match the expected word type "{self.word_type}"')
        return val


known_headers = {
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
        self.result = dict(
            lemmas=dict(ru=dict(language='ru', value=self.title)),
            lexicalCategory=Q_PART_OF_SPEECH[self.grammar_type],
            language=Q_RUSSIAN_LANG,
        )

        self.data_section = sorted(
            [(known_headers[tuple(h[1:])], t, p) for h, t, p in self.data_section],
            key=data_section_sorter)

        for header, template, params in self.data_section:
            if template not in templates:
                self.unhandled_params.update(params)
            else:
                templates[template].process(self, params)

        set_imported_from_wkt(self.result)
        for typ in ['senses', 'forms']:
            if typ in self.result:
                for val in self.result[typ]:
                    set_imported_from_wkt(val)

        return self.result

    def get_grammar_type(self):
        grammar_type = None

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
            raise ValueError(f"Unknown type {self.title}:\n{self.data_section}")
        if len(grammar_type) > 1:
            if grammar_type == root_templates['прил']:
                return 'adjective'
            raise ValueError(
                f"Multiple types found in {self.title} - {', '.join(grammar_type)}:\n{self.data_section}")
        return grammar_type.pop()

    def validate_str(self, val):
        return self.parent.validate_str(val)

    @staticmethod
    def validate_file(val):
        if not re_file.match(val):
            raise ValueError(f'File {val} does not appear to be correct')
        return val

    @staticmethod
    def validate_ipa(val):
        if not re_IPA_str.match(val):
            raise ValueError(f'IPA {val} does not appear to be correct')
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
            set_refernces_on_new(pron, {P_DESCRIBED_BY: Q_SOURCES[param_value]})

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

    def set_val(self, param_value, prop, form):
        if param_value:
            if form not in self.form_by_param:
                raise ValueError(f"form {form} does not exist, trying to set {prop}={param_value}")
            if isinstance(param_value, str):
                param_value = ClaimValue(test_str(param_value))
            prop.set_claim_on_new(self.form_by_param[form], param_value)

    def create_form(self, form_name, word, features: List[str]):
        if 'forms' not in self.result:
            self.result['forms'] = []
        stressless_word = word.replace(STRESS_SYMBOLS, '')
        form = dict(
            add='',  # without this forms are not added
            representations=dict(
                ru=dict(language='ru', value=self.validate_str(stressless_word))
            ),
            grammaticalFeatures=[Q_FEATURES[v] for v in features],
        )
        if stressless_word != word:
            self.add_pronunciation(form, word)
        self.result['forms'].append(form)
        self.form_by_param[form_name] = form

    def add_pronunciation(self, form, word):
        P_PRONUNCIATION.set_claim_on_new(form, ClaimValue(mono_value('ru', self.validate_str(word))))

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

    #
    # def add_syllables(self, params):
    #     syllables = params('слоги')
    #     if syllables is not None:
    #         P_HYPHENATION.set_claim_on_new(self.form_by_param['nom-sg'], ClaimValue(test_str(syllables)))
    #         if 'nom-sg2' in self.form_by_param:
    #             print(f"Word {self.title} has two 'nom-sg' forms, skipping second hyphenation")


templates: Dict[str, TemplateProcessorBase] = {k: v(k) for k, v in {
    'transcription-ru': TranscriptionRu,
    'transcriptions-ru': TranscriptionsRu,
    'inflection сущ ru': Noun,
    'сущ-ru': Noun,
    'сущ ru': UnknownNoun,
    'прил': Adjective,
    'по-слогам': Hyphenation,
    '_дореф': PreReformSpelling,
}.items()}
