from typing import Iterable, Dict, List

from .Cache import CacheJsonl
from .Parser import Parser
from .utils import list_to_dict_of_lists, to_json


class WikiWordParser(CacheJsonl):
    def __init__(self, file, parse_fields: Iterable[str], cache: 'Caches'):
        super().__init__(file)
        self.parse_fields = set(parse_fields) if parse_fields else None
        self.cache = cache

    def generate(self, append=False):
        with open(self.filename, "a+" if append else "w+") as file:
            if append:
                print('', file=file)
            for res in self.parse_words():
                print(to_json(res), file=file)

    def parse_words(self, words=None):
        if isinstance(words, str):
            words = [words]
        all_words = {w.title: w for w in self.cache.wiki_words.get()}
        parser = Parser(self.cache.wiki_templates.get(), self.get_existing_lexemes(), self.parse_fields)
        for word in (words or all_words):
            try:
                yield parser.parse_word(all_words[word])
            except ValueError as err:
                print(f'***** {word} *****: {err}')

    def get_existing_lexemes(self) -> Dict[str, Dict[str, List]]:
        category_ids = self.cache.lexical_categories.ids()
        # list of lexemes per grammatical category
        entities = list_to_dict_of_lists(
            (l for l in self.cache.lexemes.get() if 'ru' in l.lemmas and l.lexicalCategory in category_ids),
            lambda l: category_ids[l.lexicalCategory]
        )
        count = sum((len(v) for v in entities.values()))
        if count != len(self.cache.lexemes.get()):
            print(f'{len(self.cache.lexemes.get()) - count} entities have not been recognized')
        # convert all lists into lemma -> list, where most lists will just have one element
        return {
            k: list_to_dict_of_lists(v, lambda l: l.lemmas.ru.value)
            for k, v in entities.items()
        }
