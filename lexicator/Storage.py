import os

from lexicator.UpdateWiktionaryWithLexemeId import UpdateWiktionaryWithLexemeId
from .utils import Config
from .ResolverViaMwParse import ResolveNounRu, ResolveTranscriptionsRu, ResolveTranscriptionRu
from .PageToLexemsFilter import PageToLexemsFilter
from .PageDownloader import DownloaderForWords, DownloaderForTemplates, LexemDownloader
from .ContentStore import ContentStore
from .PageParser import PageParser


class Storage:
    def __init__(self, config: Config):
        os.makedirs("_cache", exist_ok=True)

        self.wiki_templates = ContentStore(
            '_cache/ru.wiktionary-raw-templates.db',
            DownloaderForTemplates(config))
        self.wiki_words = ContentStore(
            '_cache/ru.wiktionary-raw-words.db',
            DownloaderForWords(config))
        self.existing_lexemes = ContentStore(
            '_cache/wikidata-raw-lexemes.db',
            LexemDownloader(config))

        self.parsed_wiki_words = ContentStore(
            '_cache/parsed_ru.wiktionary.db',
            PageParser(config, self.wiki_words, config.parse_fields, self.wiki_templates))

        self.resolve_noun_ru = ContentStore(
            '_cache/resolve_noun_ru.db',
            ResolveNounRu(config, self.parsed_wiki_words))

        self.resolve_transcription_ru = ContentStore(
            '_cache/resolve_transcription_ru.db',
            ResolveTranscriptionRu(config, self.parsed_wiki_words))

        self.resolve_transcriptions_ru = ContentStore(
            '_cache/resolve_transcriptions_ru.db',
            ResolveTranscriptionsRu(config,  self.parsed_wiki_words))

        self.desired_lexemes = ContentStore(
            '_cache/expected_lexemes.db',
            PageToLexemsFilter(
                config, self.parsed_wiki_words, config.wikidata,
                {v.retriever.template_name: v for v in (
                    self.resolve_noun_ru,
                    self.resolve_transcription_ru,
                    self.resolve_transcriptions_ru,
                )}))

        self.wiktionary_updater = UpdateWiktionaryWithLexemeId(self.wiki_words, self.existing_lexemes, config)
