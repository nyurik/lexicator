"""Lexicator - Wiktionary Word Parser and Wikidata item generator

Usage:
  lexicator.py [-p <word>]...
  lexicator.py [-r <generator>]...
  lexicator.py [-v <word>]
  lexicator.py [-u <user>]
  lexicator.py (-h | --help)

Options:
  -p --parse <word>        Test-parse one or more words, checks the cache first.
  -r --refresh <generator> Reset and regenerate cached values for one or more generators.
  -v --validate <word>     Validate a single word. If <word> is a '*', validates all of them.
  -u --user <user>         Bot user name.  The password should be in ./password file. [default: YurikBot@lexicator]
  -h --help                Show this screen.
"""
from pathlib import Path

from docopt import docopt

from lexicator.Storage import Storage
from lexicator.Validator import Validator
from lexicator.utils import Config, get_site
from lexicator.wikicache import WikidataQueryService, to_json


def main(arguments):
    config = Config(
        wiktionary=get_site('ru.wiktionary.org', True),
        wikidata=get_site('www.wikidata.org', True),
        wdqs=WikidataQueryService(),
        print_warnings=True,
        verbose=False,
        # parse_fields=['acc-sg'],
    )

    password_file = Path('./password')
    if password_file.is_file():
        password = password_file.read_text().strip()
        config.wikidata.login(user=arguments['--user'], password=password, on_demand=True)
    else:
        print(f"Password file {password_file.absolute()} does not exist. Wikidata writing is disabled.")

    caches = Storage(config)
    generators = list(caches.__dict__.keys())
    for gen in arguments['--refresh']:
        if gen not in generators:
            print(f"Generator {gen} is unrecognized. Available generators: {', '.join(generators)}")
        else:
            caches.__dict__[gen].refresh()

    words_to_do = arguments['--parse']
    if words_to_do:
        caches.wiki_words.get(words_to_do)
        for word in words_to_do:
            print(f"\n================= Parsing {word}...")
            try:
                for idx, data in enumerate(caches.parsed_wiki_words.parse_words([word])):
                    if idx > 0:
                        print(f'------------ template #{idx + 1}')
                    print(to_json(data, pretty=True))
            except Exception as err:
                print(f'FAILURE: ***** {word} *****: {err}')

    word = arguments['--validate']
    if word:
        do_all = word == '*'
        if not do_all:
            print(f"\n================= Validating {word}...")
            caches.wiki_words.regenerate(append=word)
            caches.parsed_wiki_words.regenerate(append=word)
            todo = [word]
        else:
            todo = caches.parsed_wiki_words.get().keys()

        Validator(caches.parsed_wiki_words.get(), todo).run()


if __name__ == '__main__':
    main(docopt(__doc__))
