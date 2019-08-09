from typing import Iterable, Dict, List

from .Cache import CacheJsonl
from .Parser import Parser
from .utils import list_to_dict_of_lists, to_json


class Validator:
    def __init__(self, parser, words):
        self.parser = parser
        self.words = words

    def run(self):
        for word in self.words:
            if word not in self.parser:
                print(f"Word '{word}' does not exist in cache")
                continue
            word_def = self.parser[word]
            self.validate_word(word, word_def)

    def validate_word(self, word, word_def):
        for idx, form in enumerate(word_def):
            try:
                self.validate_form(word, form)
            except ValueError as err:
                print(f'ERR {word:13} {idx + 1 if idx > 0 else ""}  {err}, {form}')

    def validate_form(self, word, form):
        if len(form) == 2:
            template, params = form
            warnings = []
        elif len(form) == 3:
            template, params, warnings = form
            warnings = warnings[1:]
        else:
            raise ValueError(f'incorrect form param: {form}')

        if template != 'inflection сущ ru':
            # print(f'Skipping {word} - unrecognized template {template}')
            return

        gender = False
        if 'род' in params:
            if params['род'] == 'муж':
                gender = 'masculine'
            elif params['род'] == 'жен':
                gender = 'feminine'
            elif params['род'] == 'ср':
                gender = 'neuter'
            else:
                raise ValueError(f"unrecognized gender '{params['род']}'")

        declension = False
        if 'скл' in params:
            declension = params['скл']

        # если слово оканчивается на ь
        if word[-1] == 'ь':
            if not gender:
                raise ValueError('gender is not set')
            if not declension:
                raise ValueError('declension is not set')
            if gender == 'masculine':
                if declension != '2':
                    raise ValueError(f'masculine declension should be 2, but was {declension}')
            elif gender == 'feminine':
                if declension != '8':
                    raise ValueError(f'feminine declension should be 8, but was {declension}')
            else:
                raise ValueError(f'no declension for {gender}')
