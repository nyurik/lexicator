# lexicator
Imports Wiktionary's grammatical data into Wikidata

## Installation

Install Python 3.7 or later, clone this repo, and install dependencies with:

```bash
python3.7 -m pip install -r requirements.txt
```

## Concepts

Code is broken into modules:
* [consts](./lexicator/consts) - hardcoded constants, both common and language-specific
* [wikicache](./lexicator/wikicache) - general code lib to download and cache data
* [tokenizer](./lexicator/tokenizer) - parses raw Wiktionary pages into the list of relevant templates with their parameters. Parsers uses resolvers when needed, and can expand most of the wikitext templates until it gets to the templates it knows about.
* [lexemer](./lexicator/lexemer) - code to convert tokens into lexemes - JSON in the format of Wikidata.
* [uploader](./lexicator/uploader) - code to upload lexemes to Wikidata

Data is parsed and prepared for the upload in multiple stages.
 At each stage, a [PageRetriever](lexicator/PageRetriever.py)-derived class generates some data result.
 Page retrievers can either download or process all pages, or get just the pages changed/created since
 the last run. Each page retriever is wrapped by an instance of
 [ContentStore](lexicator/wikicache/ContentStore.py) - a generic sqlite-backed cache storage.
 All instances are stored in the [Storage](lexicator/Storage.py) singleton.

There are several types of PageRetrievers:
* **Downloaders** - uses MediaWiki API to download page content. Does minimal content processing.
  * [TemplateDownloader](./lexicator/wikicache/TemplateDownloader.py) - downloads Wiktionary templates.
  * [WiktionaryWordDownloader](./lexicator/wikicache/WiktionaryWordDownloader.py) - downloads Wiktionary word pages.
  * [LexemeDownloader](./lexicator/wikicache/LexemeDownloader.py) - downloads Lexemes in a given language. Uses WDQS to find relevant lexemes, so the data might be stale for ~1min.
* **Resolvers** - executes Lua modules via MW API in bulk to compute their results. Only works with the Lua modules that use a regular wiki template to render the results.
 For example, [Template:transcription-ru](https://ru.wiktionary.org/wiki/Шаблон:transcription-ru) converts a Russian word into an IPA transcription.
 The module takes some parameters, generates IPA string, and uses [Template:transcription](https://ru.wiktionary.org/wiki/Шаблон:transcription) to draw it on the page.
 We do not want to duplicate all that Lua code in Python, so instead we let the servers convert template parameters into usable results,
 but instead of rendering it into the hard to work with HTML, we use a fake `Template:transcription` that simply outputs the parameters it received.
 This way we can make a single API call, pass it a few hundred `{{transcription-ru|...}}`, and get back an easy-to-parse list
 of the results.

## Running

* create ./password file with the bot account
* make sure all requirements above have been installed
* Run with `python3.7 run.py`
Note that usually I have a python script that i keep modifying to do the specific aspects of importing or testing. 
