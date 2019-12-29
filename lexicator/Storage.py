from pathlib import Path

from lexicator.PageDownloader import TemplateDownloaderRu
from lexicator.PageParser import PageParser
from lexicator.PageToLexemsFilter import PageToLexemsFilter
from lexicator.Properties import Q_RUSSIAN_LANG
from lexicator.ResolverViaMwParse import ResolveNounRu, ResolveTranscriptionsRu, ResolveTranscriptionRu
from lexicator.UpdateWiktionaryWithLexemeId import UpdateWiktionaryWithLexemeId
from lexicator.WikidataUploader import WikidataUploader
from lexicator.utils import Config
from lexicator.wikicache.ContentStore import ContentStore
from lexicator.wikicache.LexemeDownloader import LexemeDownloader
from lexicator.wikicache.WiktionaryWordDownloader import WiktionaryWordDownloader


class Storage:
    def __init__(self, config: Config):
        path = Path("_cache", config.lang)
        path.mkdir(exist_ok=True, parents=True)

        log_config = config
        self.wiki_templates = ContentStore(
            path / 'wiktionary-raw-templates.db',
            TemplateDownloaderRu(config.wiktionary, log_config))
        self.wiki_words = ContentStore(
            path / 'wiktionary-raw-words.db',
            WiktionaryWordDownloader(config.wiktionary, log_config))
        self.existing_lexemes = ContentStore(
            path / 'wikidata-raw-lexemes.db',
            LexemeDownloader(config.wikidata, config.wdqs, Q_RUSSIAN_LANG, log_config))

        self.parsed_wiki_words = ContentStore(
            path / 'parsed.wiktionary.db',
            PageParser(self.wiki_words, self.wiki_templates, log_config))

        self.resolve_noun_ru = ContentStore(
            path / 'resolve_noun.db',
            ResolveNounRu(log_config, config.wiktionary, self.parsed_wiki_words))

        self.resolve_transcription_ru = ContentStore(
            path / 'resolve_transcription.db',
            ResolveTranscriptionRu(log_config, config.wiktionary, self.parsed_wiki_words))

        self.resolve_transcriptions_ru = ContentStore(
            path / 'resolve_transcriptions.db',
            ResolveTranscriptionsRu(log_config, config.wiktionary, self.parsed_wiki_words))

        self.desired_lexemes = ContentStore(
            path / 'expected_lexemes.db',
            PageToLexemsFilter(
                log_config, self.parsed_wiki_words, config.wikidata,
                {v.retriever.template_name: v for v in (
                    self.resolve_noun_ru,
                    self.resolve_transcription_ru,
                    self.resolve_transcriptions_ru,
                )}))

        self.wiktionary_updater = UpdateWiktionaryWithLexemeId(
            log_config, self.wiki_words, self.existing_lexemes, config.wiktionary)

        self.lexeme_creator = WikidataUploader(
            config.wikidata, self.desired_lexemes, self.existing_lexemes, self.wiktionary_updater)

    def delete_pages(self, pages):
        if isinstance(pages, str):
            pages = [pages]
        for val in self.__dict__.values():
            if isinstance(val, ContentStore):
                val.delete_pages(pages)
