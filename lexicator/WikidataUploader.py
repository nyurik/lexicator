from .UpdateWiktionaryWithLexemeId import UpdateWiktionaryWithLexemeId
from .Properties import Q_PART_OF_SPEECH
from .ContentStore import ContentStore
from .utils import to_json, PageContent


class WikidataUploader:

    def __init__(self, site, desired_lexemes: ContentStore, existing_lexemes: ContentStore, wiktionary_updater: UpdateWiktionaryWithLexemeId) -> None:
        self.site = site
        self.desired_lexemes = desired_lexemes
        self.existing_lexemes = existing_lexemes
        self.wiktionary_updater = wiktionary_updater
        self.__existing = None

    @property
    def existing(self):
        if self.__existing is None:
            self.__existing = {p.data: p for p in self.existing_lexemes.get_all()}
        return self.__existing

    def run(self):
        self.desired_lexemes.refresh()
        self.existing_lexemes.refresh()

        for page in self.desired_lexemes.get_all():
            if page.data and \
                    not page.content and \
                    page.title.lower() == page.title and \
                    len(page.title) > 4 and \
                    page.data[0]['lexicalCategory'] == Q_PART_OF_SPEECH['noun']:
                self._run_one(page)

    def run_one(self, word):
        self._run_one(self.desired_lexemes.get(word, True))

    def _run_one(self, page):
        for lexeme in page.data:
            word = lexeme['lemmas']['ru']['value']
            if word not in self.existing:
                lex_id = self.edit_entity(
                    lexeme,
                    f'Importing from ru.wiktionary [[wikt:ru:{page.title}|{page.title}]] using [[User:Yurik/Lexicator|Lexicator]]',
                    None)
                if lex_id:
                    self.wiktionary_updater.add_or_update_lexeme(word, lex_id)
            else:
                self.update(self.existing[word], lexeme)

    # def compare(self, old, new, *path):
    #     for p in path:
    #         if p not
    #
    # def compare(self, old, new, *path):

    def update(self, old: dict, lexeme):
        # self.edit_entity(lexeme, 'Updating from ru.wiktionary (manual pre-approval runs)')
        pass

    def edit_entity(self, data, summary, qid):
        params = dict(
            summary=summary,
            token=self.site.token(),
            data=to_json(data),
            bot=1,
            POST=1,
        )
        if qid:
            params['id'] = qid
            params['clear'] = 1
        else:
            params['new'] = 'lexeme'

        result = self.site('wbeditentity', **params)
        return result.entity.id if result.success else None
