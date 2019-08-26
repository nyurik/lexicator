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

    def run_one(self, word):
        self._run_one(self.desired_lexemes.get(word, True))

    def _run_one(self, page):
        word = page.data['lemmas']['ru']['value']
        if word not in self.existing:
            self.edit_entity(page.data, 'Importing from ru.wiktionary (manual pre-approval runs)', None)
        else:
            self.update(self.existing[word], page)

    # def compare(self, old, new, *path):
    #     for p in path:
    #         if p not
    #
    # def compare(self, old, new, *path):

    def update(self, old: dict, page: PageContent):
        new = page.data

        self.edit_entity(page.data, 'Updating from ru.wiktionary (manual pre-approval runs)')

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
