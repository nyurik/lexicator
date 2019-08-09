from typing import Union, List
from pywikiapi import Site
from .LexicalCategories import LexicalCategories
from .Cache import CacheJsonl
from .WikidataQueryService import entity_id, WikidataQueryService
from .consts import RUSSIAN_LANGUAGE
from .utils import to_json, batches


class Lexemes(CacheJsonl):

    def __init__(self,
                 filename: str,
                 site: Site,
                 wdqs: WikidataQueryService,
                 use_bot_limits: bool,
                 lexical_categories: LexicalCategories):
        super().__init__(filename)
        self.site = site
        self.wdqs = wdqs
        self.use_bot_limits = use_bot_limits
        self.lexical_categories = lexical_categories
        self.language_qid = RUSSIAN_LANGUAGE

    def generate(self, append=False):
        with open(self.filename, "w+") as file:
            batch_size = 250 if self.use_bot_limits else 50
            for batch in batches(self.existing_ids(), batch_size):
                entities = self.get_entities(batch)
                if entities:
                    print('\n'.join(to_json(item) for item in entities), file=file)

    def existing_ids(self):
        categories = self.lexical_categories.names()
        categories = {categories['noun']}

        res = self.wdqs.query(f"""\
SELECT ?lexemeId ?lemma WHERE {{
  VALUES ?category {{ {' '.join(['wd:' + c for c in categories])} }}
  ?lexemeId <http://purl.org/dc/terms/language> wd:{self.language_qid};
      wikibase:lemma ?lemma;
      wikibase:lexicalCategory ?category.
}}""")

        return {entity_id(r['lexemeId']): r['lemma']['value'] for r in res}

    def get_entities(self, ids: Union[str, List[str]]):
        expect_single = type(ids) is not list
        resp = self.site(action='wbgetentities',
                         ids=[ids] if expect_single else ids,
                         redirects='no',
                         formatversion=1)

        if 'success' in resp and resp['success'] == 1 and 'entities' in resp:
            items = [v for v in resp['entities'].values() if 'missing' not in v]
            if expect_single:
                if len(items) > 1:
                    raise ValueError('Unexpectedly got more than 1 value for a single request')
                return items[0] if len(items) == 1 else None
            return items
        else:
            return None
