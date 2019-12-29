import os

from lexicator.ContentStore import ContentStore
from lexicator.PageDownloader import DownloaderForWords, DownloaderForTemplates, LexemeDownloader
from lexicator.PageParser import PageParser
from lexicator.PageToLexemsFilter import PageToLexemsFilter
from lexicator.ResolverViaMwParse import ResolveNounRu, ResolveTranscriptionsRu, ResolveTranscriptionRu
from lexicator.UpdateWiktionaryWithLexemeId import UpdateWiktionaryWithLexemeId
from lexicator.WikidataUploader import WikidataUploader
from lexicator.utils import Config


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
            LexemeDownloader(config))

        self.parsed_wiki_words = ContentStore(
            '_cache/parsed_ru.wiktionary.db',
            PageParser(config, self.wiki_words, self.wiki_templates))

        self.resolve_noun_ru = ContentStore(
            '_cache/resolve_noun_ru.db',
            ResolveNounRu(config, self.parsed_wiki_words))

        self.resolve_transcription_ru = ContentStore(
            '_cache/resolve_transcription_ru.db',
            ResolveTranscriptionRu(config, self.parsed_wiki_words))

        self.resolve_transcriptions_ru = ContentStore(
            '_cache/resolve_transcriptions_ru.db',
            ResolveTranscriptionsRu(config, self.parsed_wiki_words))

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

        self.lexeme_creator = WikidataUploader(config.wikidata, self.desired_lexemes, self.existing_lexemes,
                                               self.wiktionary_updater)

    def delete_pages(self, pages):
        if isinstance(pages, str):
            pages = [pages]
        for val in self.__dict__.values():
            if isinstance(val, ContentStore):
                val.delete_pages(pages)
