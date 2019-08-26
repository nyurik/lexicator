import re
from typing import List, Type

from .TemplateProcessorAdjective import Adjective
from .TemplateProcessorCommon import TemplateProcessor, TranscriptionRu, TranscriptionsRu, PreReformSpelling, \
    Hyphenation
from .TemplateProcessorNouns import Noun, UnknownNoun
from .TemplateUtils import test_str
from .Properties import *
from .consts import root_templates, RUSSIAN_ALPHABET, word_types


class TemplateParser:

    def __init__(self, page, resolvers: Dict[str, 'ContentStore']) -> None:
        self.page = page
        self.resolvers = resolvers
        self.form_by_param = {}

        self.word_type: str = None
        self.grammar_type: str = None
        self.primary_form: str = None
        self.result: dict = None
        self.processed = False

    def run(self):
        try:
            grammar_type = set()
            for hdr, templ, params in self.page.data:
                if templ in root_templates and root_templates[templ]:
                    grammar_type.add(root_templates[templ])
            if not grammar_type:
                raise ValueError(f"Unknown type {self.page.title}:\n{self.page.data}")
            if len(grammar_type) > 1:
                raise ValueError(
                    f"Multiple types found in {self.page.title} - {', '.join(grammar_type)}:\n{self.page.data}")
            self.grammar_type = grammar_type.pop()

            for word_type, regex in word_types.items():
                if regex.match(self.page.title):
                    self.word_type = word_type
                    break
            else:
                raise ValueError('Unrecognized word type')

            self.result = dict(
                lemmas=dict(
                    ru=dict(language='ru', value=self.page.title)
                ),
                lexicalCategory=Q_PART_OF_SPEECH[self.grammar_type],
                language=Q_RUSSIAN_LANG,
            )

            for header, templ, params in self.page.data:
                if templ in templates:
                    runner = templates[templ](templ, self)
                    runner.process(params)

            return self.result
        except ValueError:
            # if 'noun' != self.grammar_type:
            #     return None  # Ignore non-nouns
            raise

    def validate_str(self, val):
        if not word_types[self.word_type].match(test_str(val)):
            raise ValueError(f'word {val} does not match the expected word type "{self.word_type}"')
        return val

    def set_val(self, params, val, prop, form):
        param_value = params(val)
        if param_value:
            if form not in self.form_by_param:
                raise ValueError(f"form {form} does not exist, trying to set {prop}={param_value}")
            prop.set_claim_on_new(self.form_by_param[form], ClaimValue(test_str(param_value)))

    def create_form(self, form_name, word, features: List[str]):
        if 'forms' not in self.result:
            self.result['forms'] = []
        form = dict(
            add='',  # without this forms are not added
            representations=dict(
                ru=dict(language='ru', value=self.validate_str(word))
            ),
            grammaticalFeatures=features,
        )
        self.result['forms'].append(form)
        self.form_by_param[form_name] = form
    #
    # def add_syllables(self, params):
    #     syllables = params('слоги')
    #     if syllables is not None:
    #         P_HYPHENATION.set_claim_on_new(self.form_by_param['nom-sg'], ClaimValue(test_str(syllables)))
    #         if 'nom-sg2' in self.form_by_param:
    #             print(f"Word {self.page.title} has two 'nom-sg' forms, skipping second hyphenation")


templates: Dict[str, Type[TemplateProcessor]] = {
    'transcription-ru': TranscriptionRu,
    'transcriptions-ru': TranscriptionsRu,
    'inflection сущ ru': Noun,
    'сущ-ru': Noun,
    'сущ ru': UnknownNoun,
    'прил': Adjective,
    'по-слогам': Hyphenation,
    '_дореф': PreReformSpelling,
}
