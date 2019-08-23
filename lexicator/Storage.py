import os
from dataclasses import dataclass
from typing import Union, Iterable

from pywikiapi import Site

from lexicator import WikidataQueryService
from lexicator.LuaExecutor import ResolveNounRu, ResolveTranscriptionsRu
from .LexemeMaker import LexemeMaker
from .PageDownloader import DownloaderForWords, DownloaderForTemplates, LexemDownloader
from .ContentStore import ContentStore
from .PageParser import PageParser


@dataclass
class Config:
    use_bot_limits: bool
    wiktionary: Site
    wikidata: Site
    wdqs: WikidataQueryService
    parse_fields: Union[Iterable[str], None]


class Storage:
    def __init__(self, config: Config):
        os.makedirs("_cache", exist_ok=True)

        self.wiki_templates = ContentStore(
            '_cache/ru.wiktionary-raw-templates.db', DownloaderForTemplates(config.wiktionary))
        self.wiki_words = ContentStore(
            '_cache/ru.wiktionary-raw-words.db', DownloaderForWords(config.wiktionary))
        self.existing_lexemes = ContentStore(
            '_cache/wikidata-lexemes.db',
            LexemDownloader(config.wikidata, config.wdqs))

        self.parsed_wiki_words = ContentStore(
            '_cache/ru.wiktionary-parsed-words.db',
            PageParser(self.wiki_words, config.parse_fields, self.wiki_templates))

        self.resolve_noun_ru = ContentStore(
            '_cache/resolve_noun_ru.db',
            ResolveNounRu(config.wiktionary, self.parsed_wiki_words))

        self.resolve_transcriptions_ru = ContentStore(
            '_cache/resolve_transcriptions_ru.db',
            ResolveTranscriptionsRu(config.wiktionary, self.parsed_wiki_words))

        self.desired_lexemes = ContentStore(
            '_cache/expected_lexemes.db',
            LexemeMaker(self.parsed_wiki_words, config.wikidata,
                        self.resolve_noun_ru, self.resolve_transcriptions_ru))
