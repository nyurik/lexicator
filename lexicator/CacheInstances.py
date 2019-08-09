import os

from .Config import Config
from lexicator.ParserCache import WikiWordParser
from .Lexemes import Lexemes
from .LexicalCategories import LexicalCategories
from .WikiPages import WikiPagesTemplates, WikiPagesWords


class Caches:
    def __init__(self, config: Config):
        os.makedirs("_cache", exist_ok=True)

        self.wiki_templates = WikiPagesTemplates('_cache/wiki_templates.json', config.wiktionary)
        self.wiki_words = WikiPagesWords('_cache/wiki_words.json', config.wiktionary)
        self.lexical_categories = LexicalCategories('_cache/lexical_categories.json', config.wdqs)
        self.lexemes = Lexemes('_cache/lexemes.json', config.wikidata, config.wdqs, config.use_bot_limits,
                               self.lexical_categories)

        self.parsed_wiki_words = WikiWordParser('_cache/wiki_words_parsed.json', config.parse_fields, self)
