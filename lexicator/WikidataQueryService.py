import requests


def entity_id(column):
    return column['value'][len('http://www.wikidata.org/entity/'):]


class WikidataQueryService:
    headers = {
        'Accept': 'application/sparql-results+json',
        'User-Agent': 'Lexicator Bot (User:Yurik, YuriAstrakhan@gmail.com)'
    }

    def __init__(self):
        self.rdf_url = 'https://query.wikidata.org/bigdata/namespace/wdq/sparql'

    def query(self, sparql):
        r = requests.post(self.rdf_url,
                          data=dict(query=sparql),
                          headers=self.headers)
        try:
            if not r.ok:
                print(r.reason)
                print(sparql)
                raise Exception(r.reason)
            return r.json()['results']['bindings']
        finally:
            r.close()
