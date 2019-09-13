from time import sleep

from .UpdateWiktionaryWithLexemeId import UpdateWiktionaryWithLexemeId
from .Properties import Q_PART_OF_SPEECH
from .ContentStore import ContentStore
from .utils import to_json, PageContent
import traceback

presets = {
}

pause_before = {'L' + str(int(v[1:]) - 4) for v in presets.values()}
custom_run = {'L' + str(int(v[1:]) - 1): k for k, v in presets.items()}


class WikidataUploader:

    def __init__(self, site, desired_lexemes: ContentStore, existing_lexemes: ContentStore,
                 wiktionary_updater: UpdateWiktionaryWithLexemeId) -> None:
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

        print(list(self.desired_lexemes.get_multiple(presets.keys())))

        for page in self.desired_lexemes.get_all(order_by=[self.desired_lexemes.PageContentDb.title]):
            if page.data and \
                    not page.content and \
                    page.title.lower() == page.title and \
                    page.title < 'яяяяяя' and \
                    page.title not in self.existing:
                try:
                    self._run_one_page(self.desired_lexemes.get(page.title, 'local'))
                except Exception as err:
                    print(f"Error processing {page.title}: {err}")
                    traceback.print_exc()
                    sleep(30)

    def run_one(self, word):
        self._run_one_page(self.desired_lexemes.get(word, 'all'))

    def _run_one_page(self, page):
        for lexeme_idx, lexeme_data in enumerate(page.data):
            self._run_one_lexeme(page, lexeme_idx, lexeme_data)

    def _run_one_lexeme(self, page, lexeme_idx, lexeme_data):
        word = lexeme_data['lemmas']['ru']['value']
        if lexeme_data['lexicalCategory'] != Q_PART_OF_SPEECH['noun'] and word not in presets:
            return
        lex_id = self.edit_entity(
            lexeme_data,
            f'Importing from ru.wiktionary [[wikt:ru:{page.title}|{page.title}]] using [[User:Yurik/Lexicator|Lexicator]]',
            None)
        if lex_id:
            if lex_id in pause_before:
                sleep(5)
            if lex_id in custom_run:
                self._run_one_page(self.desired_lexemes.get(custom_run[lex_id]))
                # exit(1)
            self.wiktionary_updater.add_or_update_lexeme(word, lexeme_idx, lex_id)
            sleep(1)
        # else:
        #     self.update(self.existing[word], lexeme_data)

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
