from __future__ import annotations

from typing import Set, List, TYPE_CHECKING

from lexicator.consts import Q_LANGUAGE_CODES, Q_LANGUAGE_WIKTIONARIES, root_templates, template_to_type, \
    Q_SOURCES, Q_PART_OF_SPEECH, re_file, word_types_IPA, Q_FEATURES
from lexicator.consts.ru import remove_stress
from lexicator.wikicache import json_key
from .Properties import set_references_on_new, P_IMPORTED_FROM_WM, set_qualifiers_on_new, \
    P_DESCRIBED_BY, P_PRONUNCIATION, Property, ClaimValue, mono_value, P_WORD_STEM
from .TemplateUtils import test_str

if TYPE_CHECKING:
    from .PageToLexeme import PageToLexeme


class LexemeParserState:
    def __init__(self, parent: PageToLexeme, data_section):
        self.parent = parent
        self.title = parent.title
        self.data_section = data_section
        self.unhandled_params = {}
        self.form_by_param = {}
        self.result = {}
        self.processed = False
        self.__primary_form = None

        self.grammar_type = self.get_grammar_type()
        self.extras = {}

    @property
    def primary_form(self) -> str:
        if self.__primary_form is None:
            raise ValueError('primary_form was never set')
        return self.__primary_form

    @primary_form.setter
    def primary_form(self, primary_form: str):
        self.__primary_form = primary_form

    def create_lexeme(self) -> dict:
        try:
            lex_category = Q_PART_OF_SPEECH[self.grammar_type]
        except KeyError:
            raise ValueError(f"Unhandled lexical category '{self.grammar_type}'")

        self.result['lemmas'] = {self.parent.lang_code: dict(language=self.parent.lang_code, value=self.title)}
        self.result['lexicalCategory'] = lex_category
        self.result['language'] = Q_LANGUAGE_CODES[self.parent.lang_code]

        try:
            self.data_section = sorted(
                [(self.parent.parent.known_headers[tuple(h[1:])], t, p) for h, t, p in self.data_section],
                key=self.data_section_sorter)
        except KeyError as err:
            raise ValueError(f"unknown section header {err} found")

        for header, template, params in self.data_section:
            if template not in self.parent.templates or not self.parent.templates[template].autorun:
                self.unhandled_params.update(params)
            else:
                self.run_template(template, params)

        self.set_imported_from_wkt(self.result)
        for typ in ['senses', 'forms']:
            if typ in self.result:
                for val in self.result[typ]:
                    self.set_imported_from_wkt(val)

        return self.result

    def set_imported_from_wkt(self, data):
        if 'claims' in data:
            for props in data['claims'].values():
                for claim in props:
                    set_references_on_new(claim, {P_IMPORTED_FROM_WM: Q_LANGUAGE_WIKTIONARIES[self.parent.lang_code]})

    def get_grammar_type(self) -> str:
        grammar_type: Set = set()

        def add_types(typ):
            if typ:
                nonlocal grammar_type
                if grammar_type is None:
                    grammar_type = typ.copy()
                else:
                    grammar_type.intersection_update(typ)

        for header, template, params in self.data_section:
            if template in root_templates[self.parent.lang_code]:
                add_types(root_templates[self.parent.lang_code][template])
            else:
                for rx, tp in template_to_type[self.parent.lang_code]:
                    if rx.match(template):
                        add_types(tp)
        if not grammar_type:
            raise ValueError(f"Unknown grammar type:\n{self.data_section}")
        if len(grammar_type) > 1:
            # fixme - LOCALIZE
            if grammar_type == root_templates[self.parent.lang_code]['прил']:
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
            q_sources = Q_SOURCES[self.parent.lang_code]
            try:
                refs = {P_DESCRIBED_BY: q_sources[param_value]}
            except KeyError:
                raise ValueError(f"unable to set pronunciation reference: {param_value} not found"
                                 f" in Q_SOURCES['{self.parent.lang_code}']")
            set_references_on_new(pron, refs)

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
                word = form['representations'][self.parent.lang_code]['value']
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
        form = self.create_form_obj(self.validate_str(stressless_word, 'form_representation'), features)
        if stressless_word != word:
            self.add_pronunciation(form, word)
        self.result['forms'].append(form)
        self.form_by_param[form_name] = form

    def create_form_obj(self, word_form, features):
        return dict(
            add='',  # without this forms are not added
            representations={
                self.parent.lang_code: dict(
                    language=self.parent.lang_code,
                    value=word_form,
                )
            },
            grammaticalFeatures=[Q_FEATURES[v] for v in features],
        )

    def add_pronunciation(self, form, word):
        P_PRONUNCIATION.set_claim_on_new(form, ClaimValue(
            mono_value(self.parent.lang_code, self.validate_str(word, P_PRONUNCIATION.name))))

    def resolve_lua(self, template, params):
        if template in self.parent.parent.resolvers:
            return self.parent.parent.resolvers[template].get(json_key(template, params)).data
        return params

    def split_words(self, param_value, count_expected=None):
        if self.parent.word_type == 'multi-word space-separated':
            raise ValueError(f"Not implemented word type '{self.parent.word_type}'")
        words = param_value.split(' ')
        if count_expected and len(words) != count_expected:
            raise ValueError(f'Unexpected number of words, should be {count_expected} - {words}')
        return words

    def run_template(self, template, params):
        self.parent.templates[template].process(self, params)

    def add_stem(self):
        if 'основа' in self.unhandled_params:
            P_WORD_STEM.set_claim_on_new(self.result, ClaimValue(
                mono_value(self.parent.lang_code,
                           self.validate_str(remove_stress(self.unhandled_params['основа']), 'основа'))))

    def data_section_sorter(self, values):
        header, template, params = values
        if template not in self.parent.templates:
            return 0
        return 1 if self.parent.templates[template].is_primary else 2
