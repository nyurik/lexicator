from pathlib import Path

from lexicator.lexemer.PageToLexemsFilter import PageToLexemsFilter
from lexicator.tokenizer import PageTokenizer
from lexicator.uploader import UpdateWiktionaryWithLexemeId, WikidataUploader
from lexicator.Config import Config
from lexicator.wikicache import ContentStore, LexemeDownloader, TemplateDownloader, WiktionaryWordDownloader


class Storage:
    def __init__(self, config: Config):
        path = Path("_cache", config.wiktionary.lang_code)
        path.mkdir(exist_ok=True, parents=True)

        log_config = config
        self.wiki_templates = ContentStore(
            path / 'wiktionary-raw-templates.db',
            TemplateDownloader(config.wiktionary, log_config=log_config))
        self.wiki_words = ContentStore(
            path / 'wiktionary-raw-words.db',
            WiktionaryWordDownloader(config.wiktionary, log_config))
        self.existing_lexemes = ContentStore(
            path / 'wikidata-raw-lexemes.db',
            LexemeDownloader(config.wikidata, config.wdqs, config.wiktionary.lang_code, log_config))
        self.parsed_wiki_words = ContentStore(
            path / 'parsed.wiktionary.db',
            PageTokenizer(config.wiktionary.lang_code, self.wiki_words, self.wiki_templates, log_config))
        self.desired_lexemes = ContentStore(
            path / 'expected_lexemes.db',
            PageToLexemsFilter(log_config, config.wiktionary, self.parsed_wiki_words))
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
