# lexicator
Imports Wiktionary's grammatical data into Wikidata

## Usage

Install Python 3.7 or later, clone this repo, and run these commands:

```bash
# Install required dependencies
python3.7 -m pip install -r requirements.txt

# See help
python3.7 lexicator.py --help

# Try a word
python3.7 lexicator.py -p изотоп -p барбариска

# Parse everything (will take 30-60min)
python3.7 lexicator.py -r parsed_wiki_words
```

## Caches

These caches can be refreshed using `-r`. They are stored as files in the `/_cache` dir. Deleting a file will auto-regenerate it. Using `-r` will refresh its content, unless the override `-o` is used.

cache | info
----- | ----
wiki_templates | Wiktionary templates that might be relevant to parsing.
wiki_words | All wiktionary words that use one of the "root" templates such as [inflection сущ ru](https://ru.wiktionary.org/wiki/Шаблон:inflection_сущ_ru), [падежи](https://ru.wiktionary.org/wiki/Шаблон:падежи).
lexical_categories | List of lexical categories found using a Wikidata query.
lexemes | All Wikidata lexemes in Russian, including their entire JSON.
parsed_wiki_words | Parsing results, with each word having a list of found templates with their parsed parameters and optional warnings.
