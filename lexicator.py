"""Lexicator - Wiktionary Word Parser and Wikidata item generator

Usage:
  lexicator.py [-p <word>]...
  lexicator.py [-r <generator>]... [-o] [-u <user>]
  lexicator.py (-h | --help)

Options:
  -p --parse <word>        Test-parse one or more words, checks the cache first.
  -r --refresh <generator> Reset and regenerate cached values for one or more generators.
  -o --override            If given, --refresh will override rather than append.
  -u --user <user>         Bot user name.  The password should be in ./password file. [default: YurikBot@lexicator]
  -h --help                Show this screen.
"""
from docopt import docopt
from lexicator import Config, Caches, get_site, WikidataQueryService, to_json
from pathlib import Path


def main(arguments):
    config = Config(
        use_bot_limits=False,
        wiktionary=get_site('ru.wiktionary.org'),
        wikidata=get_site('www.wikidata.org'),
        wdqs=WikidataQueryService(),
        parse_fields=None,
        # parse_fields=['acc-sg'],
    )

    password_file = Path('./password')
    if password_file.is_file():
        password = password_file.read_text().strip()
        config.wikidata.login(user=arguments['--user'], password=password, on_demand=True)
    else:
        print(f"Password file {password_file.absolute()} does not exist. Wikidata writing is disabled.")

    caches = Caches(config)
    generators = list(caches.__dict__.keys())
    for gen in arguments['--refresh']:
        if gen not in generators:
            print(f"Generator {gen} is unrecognized. Available generators: {', '.join(generators)}")
        else:
            caches.__dict__[gen].regenerate(append=not arguments['--override'])

    words_to_do = arguments['--parse']
    if words_to_do:
        caches.wiki_words.regenerate(append=words_to_do)
        for word in words_to_do:
            print(f"\n================= Parsing {word}...")
            try:
                for idx, data in enumerate(caches.parsed_wiki_words.parse_words([word])):
                    if idx > 0:
                        print(f'------------ template #{idx + 1}')
                    print(to_json(data, pretty=True))
            except Exception as err:
                print(f'FAILURE: ***** {word} *****: {err}')


if __name__ == '__main__':
    main(docopt(__doc__))
