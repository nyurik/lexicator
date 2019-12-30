from __future__ import annotations

from typing import Dict, Any

from lexicator.consts import word_types
from lexicator.wikicache import ContentStore
from .LexemeParserState import LexemeParserState
from .TemplateUtils import test_str
from .languages import templates, known_headers


class PageToLexeme:
    def __init__(self, lang_code, title, data_section, resolvers: Dict[str, ContentStore]) -> None:
        self.lang_code = lang_code
        self.title = title
        self.data_section = data_section
        self.resolvers = resolvers
        self.grammar_types = set()
        self.templates = templates[lang_code]
        self.known_headers = known_headers[lang_code]
        self.word_type: str = self.calc_word_type()

    def run(self) -> Any:
        one_lexeme = LexemeParserState(self, self.data_section)
        if one_lexeme.grammar_type in self.grammar_types:
            raise ValueError(f'More than one {one_lexeme.grammar_type} found')
        self.grammar_types.add(one_lexeme.grammar_type)

        result = one_lexeme.create_lexeme()

        if not result:
            raise ValueError('No lexemes found')
        return result

    def calc_word_type(self):
        for word_type, regex in word_types[self.lang_code].items():
            if regex.match(self.title):
                return word_type
        raise ValueError('Unrecognized word type')

    def validate_str(self, val, param):
        if not word_types[self.lang_code][self.word_type].match(test_str(val, param)):
            raise ValueError(f'word {val} does not match the expected word type "{self.word_type}"')
        return val
