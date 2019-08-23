from .ContentStore import ContentStore
from .utils import to_json, PageContent


class WikidataUploader:

    def __init__(self, site, desired_lexemes: ContentStore, existing_lexemes: ContentStore) -> None:
        self.site = site
        self.desired_lexemes = desired_lexemes
        self.existing_lexemes = existing_lexemes
        self.existing = {p.data: p for p in self.existing_lexemes.get_all()}

    def run(self):
        for page in self.desired_lexemes.get_all([self.desired_lexemes.PageContentDb.content is None]):
            self._run_one(page)

    def run_one(self, word, qid=None):
        self._run_one(self.desired_lexemes.get(word, True), qid)

    def _run_one(self, page, qid=None):
        word = page.data['lemmas']['ru']['value']
        if word not in self.existing or qid:
            self.upload(page, qid)

    def upload(self, page: PageContent, qid):
        self.edit_entity(page.data, 'Importing from ru.wiktionary (manual pre-approval runs)', qid)

    def edit_entity(self, data, summary, qid):
        params = dict(
            summary=summary,
            token=self.site.token(),
            data=to_json(data),
            # bot=1,
            POST=1,
        )
        if qid:
            params['id'] = qid
            params['clear'] = 1
        else:
            params['new'] = 'lexeme'

        result = self.site('wbeditentity', **params)
        return result.entity.id if result.success else None
