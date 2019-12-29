from mwparserfromhell import parse as mw_parse
from mwparserfromhell.nodes import Template, Text, Tag, Wikilink, Heading, HTMLEntity, Comment, ExternalLink

from lexicator.utils import list_to_dict_of_lists
from lexicator.wikicache import ContentStore
from lexicator.wikicache.utils import MwSite, LogConfig

IGNORE_TYPES = {Text, Tag, Wikilink, Comment, ExternalLink, HTMLEntity}
LEX_TEMPLATE = 'Лексема в Викиданных'

ignore_words = {
}


def format_lex_ref(lexeme_id):
    return f'{{{{{LEX_TEMPLATE}|{lexeme_id}}}}}'


class UpdateWiktionaryWithLexemeId:
    def __init__(self, log_config: LogConfig, wiki_words: ContentStore, existing_lexemes: ContentStore,
                 wiktionary: MwSite) -> None:
        self.log_config = log_config
        self.wiki_words = wiki_words
        self.existing_lexemes = existing_lexemes
        self.site = wiktionary

    def run(self):
        self.wiki_words.refresh()
        self.existing_lexemes.refresh()
        for word, lexemes in list_to_dict_of_lists(self.existing_lexemes.get_all(), lambda l: l.data).items():
            self.run_one_word(word, lexemes)

    def run_one_word(self, word, lexemes=None):
        if word in ignore_words:
            return
        if lexemes is None:
            lexemes = self.existing_lexemes.get_all(
                filters=self.existing_lexemes.PageContentDb.data == to_json(word),
            )
        lex_ids = [lex.title[len('Lexeme:'):] for lex in lexemes]
        try:
            page = self.wiki_words.get(word)
        except KeyError:
            print(f"Word {word} does not exist in Wiktionary, orphaned lexemes: {lex_ids}")
            return
        if all((format_lex_ref(v) in page.content for v in lex_ids)):
            return
        print(f"Updating {word} with {lex_ids}")
        for idx, lexeme_id in enumerate(lex_ids):
            try:
                self.add_or_update_lexeme(word, idx, lexeme_id)
            except ValueError as err:
                print(f'{word}: {err}')
            except Exception as err:
                print(f'{word} failed with {err}')
                # raise

    def add_or_update_lexeme(self, word: str, lexeme_idx: int, lexeme_id: str):
        page = self.wiki_words.get(word, 'all' if lexeme_idx > 0 else False)
        if not page:
            raise ValueError(f'Page {word} does not exist')
        if page.title != word:
            raise ValueError(f'Page {word} redirects to {page.title}, orphaned lexeme {lexeme_id}')
        lex_link = format_lex_ref(lexeme_id)
        content = page.content

        code = mw_parse(content)
        placeholder = None
        inside_ru_section = None
        inside_meaning = None
        for arg in code.filter(recursive=False):
            typ = type(arg)
            if typ in IGNORE_TYPES:
                continue
            elif typ == Template:
                name = str(arg.name).strip()
                if name.startswith('Шаблон:') or name.startswith('шаблон:'):
                    name = name[len('шаблон:'):]
                if name == LEX_TEMPLATE and (inside_meaning or 0) == lexeme_idx:
                    page_lex_id = str(arg.get(1)).strip()
                    if page_lex_id == lexeme_id:
                        if self.log_config.verbose:
                            print(f'Word {word} already has lexeme = {lexeme_id}, skipping')
                        return
                    else:
                        raise ValueError(f'Word {word} uses Lexeme = {page_lex_id}, but {lexeme_id} is expected')
            elif typ == Heading:
                if arg.level == 1:
                    if str(arg.title).strip() == '{{-ru-}}':
                        if inside_ru_section is not None or placeholder is not None:
                            raise ValueError(f'Multiple {{{{-ru-}}}} sections found in {word}, or unexpected sections')
                        inside_ru_section = True
                        if lexeme_idx == 0:
                            placeholder = arg
                    elif inside_ru_section:
                        inside_ru_section = False
                elif inside_ru_section:
                    if arg.level == 2:
                        hdr_title = str(arg.title).strip()
                        if not hdr_title.startswith('{{заголовок|') and not hdr_title.startswith('{{з|'):
                            raise ValueError(f'Unexpected lvl2 header {arg.title}')
                        if inside_meaning is None:
                            inside_meaning = 0
                        else:
                            inside_meaning += 1
                        if inside_meaning == lexeme_idx:
                            placeholder = arg
            else:
                print(f'Unexpected element in the header - {typ} -- {arg}')

        if not placeholder:
            raise ValueError(f'unable to find where to insert {lexeme_id} (#{lexeme_idx + 1})')

        code.insert_after(placeholder, '\n' + lex_link)
        desired_content = str(code)
        if page.content != desired_content:
            summary = f'добавлена ссылка на лексему [[d:Lexeme:{lexeme_id}]]'
            if inside_meaning is not None:
                summary += f' значение {lexeme_idx + 1}'
            result = self.site(
                'edit',
                title=word,
                summary=summary,
                token=self.site.token(),
                text=desired_content,
                basetimestamp=page.timestamp,
                starttimestamp=page.timestamp,
                bot=True,
                minor=True,
                nocreate=True,
            )
            if result.edit.result != 'Success':
                raise ValueError(result)
            else:
                print(f'ru.wiktionary {word}: {summary}')
