from lexicator.Cache import CacheJsonl
from lexicator.WikidataQueryService import WikidataQueryService, entity_id
from lexicator.utils import to_json


class LexicalCategories(CacheJsonl):

    def __init__(self, filename: str, wdqs: WikidataQueryService):
        super().__init__(filename)
        self.wdqs = wdqs

    def generate(self, append=False):
        result = self.wdqs.query('''\
SELECT ?id ?idLabel WHERE {  
  ?id wdt:P31 wd:Q82042.
  SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
}''')

        with open(self.filename, "w+", encoding='utf-8') as file:
            print('\n'.join(to_json((entity_id(r['id']), r['idLabel']['value'])) for r in result), file=file)

    def load(self):
        ids_to_names = {v[0]: v[1] for v in super().load()}
        names_to_ids = {v: k for k, v in ids_to_names.items()}
        return names_to_ids, ids_to_names

    def names(self):
        return self.get()[0]

    def ids(self):
        return self.get()[1]
