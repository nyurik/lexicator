from __future__ import annotations

from typing import Any, TYPE_CHECKING

from lexicator.consts import word_types
from .LexemeParserState import LexemeParserState
from .TemplateUtils import test_str
from .common import templates

if TYPE_CHECKING:
    from . import PageToLexemsFilter


class PageToLexeme:
    def __init__(self, parent: PageToLexemsFilter, title, data_section) -> None:
        self.parent = parent
        self.lang_code = parent.lang_code
        self.title = title
        self.data_section = data_section
        self.grammar_types = set()
        self.templates = templates[self.lang_code]
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
