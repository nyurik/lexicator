from pathlib import Path

from lexicator.Storage import Storage
from lexicator.utils import Config, get_site
from lexicator.wikicache import WikidataQueryService

config = Config(
    wiktionary=get_site('ru.wiktionary.org', True),
    wikidata=get_site('www.wikidata.org', True),
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
s.desired_lexemes.refresh()

# s.lexeme_creator.run()
