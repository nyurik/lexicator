from mwparserfromhell import parse as mw_parse
from mwparserfromhell.nodes import Template, Text, Tag, Wikilink, Heading, HTMLEntity, Comment, ExternalLink
from pywikiapi import Site

IGNORE_TYPES = {Text, Tag, Wikilink, Comment, ExternalLink, HTMLEntity}
LEX_TEMPLATE = 'Лексема в Викиданных'


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
            lexeme_id = lex.title[len('Lexeme:'):]
            try:
                self.add_or_update_lexeme(word, lexeme_id)
            except ValueError as err:
                print(f'{word}: {err}')

    def add_or_update_lexeme(self, word: str, lexeme_id: str):
        page = self.wiki_words.get(word)
        if not page:
            raise ValueError(f'Page {word} does not exist')
        lex_link = f'{{{{{LEX_TEMPLATE}|{lexeme_id}}}}}'
        content = page.content
        # content = re.sub(re.escape(lex_link) + r'\n+', '', content).lstrip()
        code = mw_parse(content)
        placeholder = None
        for arg in code.filter(recursive=False):
            typ = type(arg)
            if typ in IGNORE_TYPES:
                continue
            elif typ == Template:
                name = str(arg.name).strip()
                if name.startswith('Шаблон:') or name.startswith('шаблон:'):
                    name = name[len('шаблон:'):]
                if name == LEX_TEMPLATE:
                    page_lex_id = str(arg.get(1)).strip()
                    if page_lex_id == lexeme_id:
                        if self.verbose:
                            print(f'Word {word} already has lexeme = {lexeme_id}, skipping')
                        return
                    else:
                        raise ValueError(f'Word {word} uses Lexeme = {page_lex_id}, but {lexeme_id} is expected')
            elif typ == Heading:
                if arg.level == 1 and str(arg.title).strip() == '{{-ru-}}' and placeholder is None:
                    placeholder = arg
                elif placeholder:
                    code.insert_after(placeholder, '\n' + lex_link)
                    placeholder = False
            else:
                print(f'Unexpected element in the header - {typ} -- {arg}')

        desired_content = str(code)
        if page.content != desired_content:
            # our template not found in the header, make sure it does not exist at all
            result = self.site(
                'edit',
                title=word,
                summary=f'добавлена ссылка на Лексему [[d:Lexeme:{lexeme_id}]]',
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
                print(f'Word {word} has been modified to link to {lexeme_id}')
