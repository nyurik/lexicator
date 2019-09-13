from mwparserfromhell import parse as mw_parse
from mwparserfromhell.nodes import Template, Text, Tag, Wikilink, Heading, HTMLEntity, Comment, ExternalLink

IGNORE_TYPES = {Text, Tag, Wikilink, Comment, ExternalLink, HTMLEntity}
LEX_TEMPLATE = 'Лексема в Викиданных'

ignore_words = {
    'антилидер',
}


class UpdateWiktionaryWithLexemeId:

    def __init__(self, wiki_words, existing_lexemes, config) -> None:
        self.wiki_words = wiki_words
        self.existing_lexemes = existing_lexemes
        self.site = config.wiktionary
        self.verbose = config.verbose

    def run(self):
        self.wiki_words.refresh()
        self.existing_lexemes.refresh()
        for lex in self.existing_lexemes.get_all():
            word = lex.data
            if word in ignore_words:
                continue
            lexeme_id = lex.title[len('Lexeme:'):]
            try:
                self.add_or_update_lexeme(word, lexeme_id)
            except ValueError as err:
                print(f'{word}: {err}')
            except Exception:
                print(f'{word} failed')
                raise

    def add_or_update_lexeme(self, word: str, lexeme_idx: int, lexeme_id: str):
        page = self.wiki_words.get(word, 'all')
        if not page:
            raise ValueError(f'Page {word} does not exist')
        lex_link = f'{{{{{LEX_TEMPLATE}|{lexeme_id}}}}}'
        content = page.content
        # content = re.sub(re.escape(lex_link) + r'\n+', '', content).lstrip()
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
                if name == LEX_TEMPLATE and placeholder:
                    page_lex_id = str(arg.get(1)).strip()
                    if page_lex_id == lexeme_id:
                        if self.verbose:
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
            raise ValueError(f'Unable to find where to insert the header for {word}')

        code.insert_after(placeholder, '\n' + lex_link)
        desired_content = str(code)
        if page.content != desired_content:
            summary = f'добавлена ссылка на Лексему [[d:Lexeme:{lexeme_id}]]'
            if inside_meaning is not None:
                summary += f' значение {lexeme_idx + 1}'
            result = self.site(
                'edit',
                title=word,
                summary=summary,
                token=self.site.token(),
                text=desired_content,
                basetimestamp=page.timestamp,
                bot=True,
                minor=True,
                nocreate=True,
            )
            if result.edit.result != 'Success':
                raise ValueError(result)
            else:
                print(f'ru.wiktionary {word}: {summary}')
