import json
import traceback
from typing import Set

from time import sleep

from lexicator.ContentStore import ContentStore
from lexicator.Properties import Q_PART_OF_SPEECH
from lexicator.UpdateWiktionaryWithLexemeId import UpdateWiktionaryWithLexemeId
from lexicator.utils import to_json

presets = {
}

pause_before = {'L' + str(int(v[1:]) - 4) for v in presets.values()}
custom_run = {'L' + str(int(v[1:]) - 1): k for k, v in presets.items()}

allowed_types = {Q_PART_OF_SPEECH[t] for t in [
    'noun',
]}


class WikidataUploader:

    def __init__(self, site, desired_lexemes: ContentStore, existing_lexemes: ContentStore,
                 wiktionary_updater: UpdateWiktionaryWithLexemeId) -> None:
        self.site = site
        self.desired_lexemes = desired_lexemes
        self.existing_lexemes = existing_lexemes
        self.wiktionary_updater = wiktionary_updater
        self.__existing = None

    @property
    def existing(self) -> Set[str]:
        if self.__existing is None:
            self.__existing = {json.loads(p[0]) for p in self.existing_lexemes.get_all(
                filters=[
                    self.existing_lexemes.PageContentDb.redirect.is_(None),
                    self.existing_lexemes.PageContentDb.content.isnot(None),
                ],
                columns=[
                    self.existing_lexemes.PageContentDb.data,
                ])}
        return self.__existing

    def run(self):
        self.desired_lexemes.refresh()
        self.existing_lexemes.refresh()

        print(list(self.desired_lexemes.get_multiple(presets.keys())))

        for page in self.desired_lexemes.get_all(
                filters=[
                    self.desired_lexemes.PageContentDb.data.isnot(None),
                    # self.desired_lexemes.PageContentDb.content.is_(None),
                    self.desired_lexemes.PageContentDb.redirect.is_(None),
                ],
                order_by=[self.desired_lexemes.PageContentDb.title]):
            if (
                    page.data is not None and
                    # page.content is None and
                    page.redirect is None and
                    page.title.lower() == page.title and
                    page.title < 'яяяяяя' and
                    page.title not in self.existing and
                    page.title not in presets and
                    any(('lexicalCategory' in v and v['lexicalCategory'] in allowed_types for v in page.data))
            ):
                # page.content is None
                try:
                    self._run_one_page(page.title, self.desired_lexemes.get(page.title, 'local'))
                except Exception as err:
                    print(f"Error processing {page.title}: {err}")
                    traceback.print_exc()
                    sleep(30)

    def run_one(self, word):
        self._run_one_page(word, self.desired_lexemes.get(word, 'all'))

    def _run_one_page(self, word, page):
        for lexeme_idx, lexeme_data in enumerate(page.data):
            self._run_one_lexeme(word, page, lexeme_idx, lexeme_data)

    def _run_one_lexeme(self, word, page, lexeme_idx, lexeme_data):
        if word != lexeme_data['lemmas']['ru']['value']:
            raise ValueError(f"Unable to create word {word} - lexeme is for {lexeme_data['lemmas']['ru']['value']}")
        print(f"Creating {word} {f'#{lexeme_idx}' if lexeme_idx > 0 else ''}")
        lex_id = self.edit_entity(
            lexeme_data,
            f'Importing from ru.wiktionary [[wikt:ru:{page.title}|{page.title}]] using [[User:Yurik/Lexicator|Lexicator]]',
            None)
        if lex_id:
            if lex_id in pause_before:
                sleep(5)
            if lex_id in custom_run:
                custom_word = custom_run[lex_id]
                self._run_one_page(custom_word, self.desired_lexemes.get(custom_word))
            self.wiktionary_updater.add_or_update_lexeme(word, lexeme_idx, lex_id)
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
