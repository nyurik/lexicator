from pathlib import Path

from lexicator import get_site, WikidataQueryService, Config
from lexicator.Storage import Storage
from lexicator.WikidataUploader import WikidataUploader

config = Config(
    use_bot_limits=True,
    wiktionary=get_site('ru.wiktionary.org'),
    wikidata=get_site('www.wikidata.org'),
    wdqs=WikidataQueryService(),
    print_warnings=True,
    verbose=False,
)

config.wikidata.login('YurikBot@lexicator', password=Path('./.password').read_text().strip(), on_demand=True)
config.wikidata.maxlag = 2
config.wiktionary.login('YurikBot@lexicator', password=Path('./.password').read_text().strip(), on_demand=True)
config.wiktionary.maxlag = 2

s = Storage(config)

s.wiki_templates.refresh()
s.wiki_words.refresh()
s.existing_lexemes.refresh()
s.parsed_wiki_words.refresh()
s.resolve_transcriptions_ru.custom_refresh()
s.resolve_transcription_ru.custom_refresh()
s.resolve_noun_ru.custom_refresh()
s.desired_lexemes.refresh()

u = WikidataUploader(config.wikidata, s.desired_lexemes, s.existing_lexemes, s.wiktionary_updater)
u.run()