import re
import unicodedata
from dataclasses import dataclass
from typing import Callable, Union

from mwparserfromhell.wikicode import Wikicode

NS_MAIN = 0
NS_USER = 2
NS_USER_TALK = 3
NS_TEMPLATE = 10
NS_TEMPLATE_TALK = 11
NS_LEXEME = 146

HTML_BR_TAGS = {'<br>', '<br >', '<br/>', '<br />'}

re_template_names = re.compile(
    r'^(([tT]emplate|[шШ]аблон):)?' +
    r'('
    r'([iI]nflection )?[сС]ущ[- _]+ru([ +]?$|[ +][^/\n]*(//)?[^/\n]*$)'
    r'|сущ n '
    r'|[пП]рил ru'
    r'|гл[ _]ru[ _]'
    r'|[гГ]л-блок2наст'
    r'|Мс-'
    r'|[тТ]аблица склонения ru .*'
    r'|[Фф]ам([- _]\w+)+'
    r'|прил[ _]ru'
    r'|прич[ _]ru([- _]\w+)*'
    r'|мест[ _]ru'
    r'|числ[ _]ru([- _]\w+)*'
    r'|числ-'
    r'|[кК]ол[ _]чис '
    r')')

RUSSIAN_STRESSABLE_LETTERS = 'аАеЕиИоОуУэЭюЮяЯ'
RUSSIAN_ALPHABET = 'аАбБвВгГдДеЕёЁжЖзЗиИйЙкКлЛмМнНоОпПрРсСтТуУфФхХцЦчЧшШщЩъЪыЫьЬэЭюЮяЯ'
RUSSIAN_ALPHABET_EXT = 'ѕЅіІѣѡѠѢѧѦѩѨѫѪѭѬѯѮѱѰѳѲѵѴ'
STRESS_SYMBOL_PRI = '\u0301'
STRESS_SYMBOL_SEC = '\u0300'
RUSSIAN_ALHABET_STRESS = \
    RUSSIAN_ALPHABET + STRESS_SYMBOL_PRI + STRESS_SYMBOL_SEC + unicodedata.normalize(
        'NFC',
        ''.join(((v + STRESS_SYMBOL_PRI + v + STRESS_SYMBOL_SEC) for v in RUSSIAN_STRESSABLE_LETTERS)))

re_russian_word_suspect = re.compile(f'[{RUSSIAN_ALPHABET}{RUSSIAN_ALPHABET_EXT}]')

re_russian_word = re.compile(rf'^[{RUSSIAN_ALHABET_STRESS}]+$')
word_types = {
    'letters only': re_russian_word,
    'multi-word dash-separated': re.compile(rf'^[{RUSSIAN_ALHABET_STRESS}]+(-[{RUSSIAN_ALHABET_STRESS}]+)+$'),
    'multi-word space-separated': re.compile(rf'^[{RUSSIAN_ALHABET_STRESS}]+( [{RUSSIAN_ALHABET_STRESS}]+)+$'),
}

re_file = re.compile(r'^[^<>]+\.(ogg|wav|mp3)$')

# From http://www.internationalphoneticalphabet.org/ipa-charts/ipa-symbols-with-unicode-decimal-and-hex-codes/
IPA_SYMBOLS = '‿⁽⁾()abcdefghijklmnopqrstuvwxyzɑɐɒæɓʙβɔɕçɗɖðʤəɘɚɛɜɝɞɟʄɡɠɢʛɦɧħɥʜɨɪʝɭɬɫɮʟɱɯɰŋɳɲɴøɵɸθœɶʘɹɺɾɻʀʁɽʂʃʈʧʉʊʋⱱʌɣɤʍχʎʏʑʐʒʔʡʕʢǀǁǂǃˈˌːˑʼʴʰʱʲʷˠˤ˞ɫ↓↑→↗↘\u0325\u030A\u0324\u032A\u032C\u0330\u033A\u033C\u033B\u031A\u0339\u0303\u031C\u031F\u0320\u0308\u0334\u033D\u031D\u0329\u031E\u032F\u0318\u0319\u0306\u030B\u0301\u0304\u0300\u030F\u035C\u0361'
re_IPA_str = re.compile(rf'^[{IPA_SYMBOLS}]+$')


# re_extra_templates = r'^([tT]emplate|[шШ]аблон):(' + '|'.join(['падежи', 'кавычки']) + ')$'


def title_case_re(title):
    if title[0].isalpha():
        return f'[{title[0].upper()}|{title[0].lower()}]{title[1:]}'
    return title


def double_title_case(dataset: Union[set, dict]):
    for title in list(dataset):
        if title[0].isalpha():
            if title[0].islower():
                add = title[0].upper() + title[1:]
            else:
                add = title[0].lower() + title[1:]
            if isinstance(dataset, set):
                dataset.add(add)
            else:
                dataset[add] = dataset[title]


root_templates = {
    k: None if not v else {v} if isinstance(v, str) else v for k, v in {
        'abbrev': 'abbreviation',
        'прил': {'adjective', 'participle'},  # прилагательное, причастие
        'наречие': 'adverb',
        'adv ru': 'adverb',  # наречие
        'conj ru': 'conjunction',  # союз
        'interj ru': 'interjection',  # междометие
        'interj-ru': 'interjection',  # междометие
        'inflection сущ ru': 'noun',
        'сущ ru': 'noun',
        'сущ-ru': 'noun',
        'топоним': 'noun',
        'фам': 'noun',
        'Фам-блок': 'noun',
        'гидроним': 'noun',
        'числ': 'number',
        'числ ru 7-8-десят': 'number',
        'числ-5': 'number',
        'onomatop ru': 'onomatopoeia',
        'прич.': 'participle',  # причастие
        'part ru': 'particle',  # частица
        'predic ru': 'predicate',  # сказуемое
        'prep ru': 'preposition',  # предлог
        'suffix ru': 'suffix',
        'гл ru': 'verb',
        'Гл-блок': 'verb',
        'спряжения': 'verb',
        'деепр ru': 'transgressive',  # деепричастие
        'дееприч.': 'transgressive',  # деепричастие

        '-ся': '', '=': '', 'alt': '', 'anim': '', 'cf': '', 'morph': '', 'phrase': '', 'transcription-ru': '',
        'transcriptions-ru': '', 'астроним': '', 'действие': '', 'илл': '', 'медиа': '', 'морфема': '', 'морфо': '',
        'морфо-ru': '', 'не путать': '', 'омонимы': '', 'омофоны': '', 'омоформы': '', 'омоформы02': '', 'орфоэпия': '',
        'падежи': '', 'превосх.': '', 'свойство': '', 'собств.': '', 'сокращ': '', 'сравн.': '', 'страд.': '',
        'также': '', 'не так': '', 'актанты': '', 'intro ru': '', 'init': '', 'неё': '', 'степени сравнения': '',
        'совершить': '', 'См': '', 'transcription': '', 'множ.': '', 'по-слогам': '', 'по слогам': '',
        'падежи ru 1': '', 'падежи ru m n f pl': '', 'слоги': '', 'Лексема в Викиданных': '',
    }.items()
}

template_to_type = [
    (re.compile(r'^_прич .*'), {'participle'}),
]

re_template_name_suspect = re.compile(r'^(([tT]emplate|[шШ]аблон):)?[сС]ущ[ _]')
re_root_templates = re.compile('|'.join((title_case_re(v) for v in root_templates)))
re_root_templates_full_str = re.compile(r'^(' + '|'.join((title_case_re(v) for v in root_templates)) + r')$')
double_title_case(root_templates)

known_headers = ['-sla-pro-', '-ru-', '-ru-old-']
re_known_headers = re.compile('|'.join((v for v in known_headers)))

root_header_templates = {
    'з', 'заголовок',
}

re_ignore_template_prefixes = re.compile(
    r'^('
    r'DEFAULTSORT:|[эЭ]тимология:|[рР]одств:|[гГ]ипонимы:|[сС]инонимы:'
    r'|#lst:|formatnum:|[мМ]ета:|[кК]нига:|[мМ]етаграммы:|родств-'
    r')')

ignore_templates = {
    '-', '--', '--+', '-ание', '-атель', '-ация', '-ение', '-ист', '-ка', '3л.', '?', '??', '^', 'addoncat', 'anchor',
    'aslinks', 'bagua nav', 'Brückner', 'cite web', 'clear', 'comment', 'commons', 'Cquote', 'Cyrs', 'de', 'en', 'es',
    'ESJČ', 'etym-lang', 'f', 'f60', 'fonts', 'forms', 'fr', 'fr0', 'fr1', 'fr2', 'fr4', 'fr6', 'frD', 'frE', 'freq',
    'frF', 'i-a', 'improve', 'incorrect', 'inflection сущ ru/text', 'it', 'Jpan', 'Karulis', 'key', 'lang', 'lang-ar',
    'lang-el', 'lang-en', 'lang-es', 'lang-grc', 'lang-he', 'lang2', 'letter disp2', 'letter_disp2', 'm', 'MAC',
    'main other', 'multilang', 'n', 'ngram ru', 'nl', 'nobr', 'OED', 'off', 'offensive', 'offensive-block',
    'offensive-inline', 'Old-ru', 'Oxford', 'pl', 'pt', 'razr', 'reflist', 'Script/Slavonic', 'sla-pro', 'stub', 'sv',
    't', 'table-bot', 'table-mid', 'table-top', 'tblV', 'term', 'tradu', 'transcriptions', 'uk', 'unfinished',
    'verb-dir', 'verb-dir-n', 'wikify', 'wikipedia', 'zh', 'аббр.', 'Аванесов1988', 'авиац.', 'авто', 'авто.жарг.',
    'автомоб. жарг.', 'автомоб.', 'автор', 'Агеенко', 'агрон.', 'Адамчик', 'адъект.', 'адъектив.', 'Академия-1',
    'Академия-2', 'Академия-3', 'алхим.', 'альп.', 'амер.', 'анат.', 'анатом.', 'Аникин', 'антроп.', 'Арапова',
    'арм. жарг.', 'арм.', 'артилл.', 'арх.', 'археол.', 'архит.', 'архитект.', 'астрол.', 'астрон.', 'аудио', 'аффиксы',
    'БАС', 'Без употребления', 'безл.', 'библ.', 'библейск.', 'библио', 'Библия', 'Библия2', 'биол.', 'биохим.',
    'бирж.', 'болг.', 'бот.', 'ботан.', 'бран.', 'бранн.', 'БСКСРЯ', 'БСЭ-1', 'БСЭ-2', 'БТС', 'Буй', 'букв.', 'бухг.',
    'Быть', 'в три колонки', 'варианты', 'вводн.', 'вет.', 'википед.', 'Википедия', 'вин.', 'Виноградов', 'воен. жарг.',
    'воен.', 'военн. жарг.', 'военн.', 'возвр.', 'врезка', 'вставить переводы', 'ВТ-Даль', 'втч', 'вульг.', 'выдел',
    'высок.', 'Ганжина', 'гастрон.', 'ген.', 'генет.', 'геогр.', 'геод.', 'геол.', 'геом.', 'геометр.',
    'геометрические фигуры', 'геофиз.', 'геральд.', 'гидрол.', 'гидротехн.', 'гипокор.', 'горн.', 'грам.', 'Графика',
    'Грачёв', 'греческая буква', 'гру', 'груб.', 'ГСРЯ', 'Даль', 'Даль-3', 'дат', 'деепр.', 'детск.', 'диал.', 'дипл.',
    'дисфм.', 'длина слова', 'Дядечко', 'ед. ч.', 'ед.', 'Елистратов', 'Епишкин', 'ЕСУМ5', 'Еськова', 'Ефремова', 'ж.',
    'ж.-д.', 'жарг. гом.', 'жарг. ЛГБТ', 'жарг. нарк.', 'жарг.', 'жаргон википроектов', 'жаргон ФВМ', 'ЖД', 'жд',
    'женск.', 'Живая речь', 'живоп.', 'животн.', 'Жуков, 1991', 'журн.', 'Зайцева 2013', 'Зарва2001', 'звукоподр',
    'Знаки Зодиака', 'значение', 'значение?', 'зоол.', 'И-МАС', 'И-Рез', 'И-СТСЕ', 'игр.', 'из', 'илл-знак', 'иноск.',
    'интервалы', 'интернет.', 'информ.', 'ирон.', 'иск.', 'искаж.', 'искусств.', 'ист.', 'истор.', 'История Японии',
    'Источники', 'исч.', 'итд', 'итп', 'ихтиол.', 'йогич.', 'кавычки', 'канц.', 'карт.', 'картеж.жарг.', 'категория',
    'Категория', 'Квеселевич', 'КЕ', 'керам.', 'кино', 'кинол.', 'книга', 'Книга:Апрес95', 'Книга:Квеселевич',
    'Книга:Ключевые идеи', 'Книга:Мельчук', 'книжн.', 'кол', 'комп. жарг.', 'комп.', 'комп.жарг.', 'конев.',
    'конец кол', 'Коровушкин', 'косм.', 'космет.', 'крим.    жарг.', 'крим. жарг.', 'крим.', 'Крылов', 'кс', 'КСИЯ-2',
    'кубан.', 'Кузнецова и Ефремова', 'кулин.', 'культурол.', 'ласк.', 'Лебедева', 'лес.', 'лики святости ru', 'лингв.',
    'лит.', 'литер.', 'лог.', 'м.', 'марр', 'МАС', 'МАС2', 'мат', 'матем.', 'машин.', 'мед.', 'Мельчук', 'местн.',
    'месяцы FR', 'месяцы', 'метаграммы:*ело', 'металл.', 'метео', 'метеор.', 'метеорол.', 'метоним.', 'мех.', 'микол.',
    'микробиол.', 'милиц. жарг.', 'мин.', 'минер.', 'минерал.', 'мир, смирный', 'миф.', 'мифол.', 'мкб.', 'мн',
    'мн. ч.', 'мн.', 'мн.ч.', 'многокр.', 'Мокиенко', 'Мокиенко, Никитина 2007', 'мол.', 'мор.', 'морск.', 'муз. жарг.',
    'муз.', 'музы', 'мфа?', 'Навигация', 'наказания', 'нар.-поэт.', 'нар.-разг.', 'нареч.', 'нарк.', 'насл', 'научн.',
    'неделя', 'неисч.', 'неодобр.', 'неодуш.', 'неол.', 'неофиц.', 'неперех.', 'неправ.', 'нескл.', 'несов.',
    'нет примеров', 'неуп.', 'неуст', 'нефт.', 'нефтегаз.', 'Никитина', 'Никонов', 'НОСС', 'ноты', 'НСЗ-60', 'НСЗ-70',
    'НСЗ-80', 'НСЗ-90', 'Нужен перевод', 'нумизм.', 'обл.', 'образ.', 'обсц.', 'однокр.', 'одобр.', 'одуш.',
    'Ожегов-28', 'оккульт.', 'опт.', 'орнит.', 'орнитол.', 'оскорбит.', 'ОСРЯ', 'от', 'отн.', 'отсылка', 'отчество',
    'офиц.', 'охотн.', 'ОЭСРЯ-10', 'п.', 'пал.', 'палеонт.', 'палеонтол.', 'парикмах.', 'перев-блок', 'переводы',
    'перен.', 'перех.', 'Периодическая система элементов', 'плотн.', 'Плуцер', 'по', 'полигр.', 'полит. жарг.',
    'полит.', 'полит.жарг.', 'полиц. жарг.', 'помета', 'помета.', 'порт.', 'портн.', 'Поспелов-ГНМ', 'Поспелов-ГНР',
    'поэт.', 'прагерм', 'праиндоевр', 'праслав', 'предик.', 'прежде', 'презр.', 'презрит.', 'пренебр.', 'прил-сравн ru',
    'прил0', 'пример', 'примечания', 'приставки СИ', 'причастие', 'прогр.', 'произв', 'прост.', 'прото', 'проф.',
    'прочее-блок', 'психиатр.', 'психол.', 'публ.', 'публиц.', 'пчел.', 'радио', 'радиоэл.', 'разг.', 'рег.', 'редк.',
    'результат', 'рекл.', 'рел.', 'религ.', 'РЖ', 'ритор.', 'РОС-4', 'Россия', 'Рус.грамматика-80', 'русские падежи',
    'русские приставки', 'Русский алфавит', 'рыбол.', 'РЭС', 'с.-х.', 'С:orv:Срезневский', 'С:ru:Фасмер', 'С:ru:Черных',
    'С:ru:Шанский', 'сад.', 'Сазонова', 'СГНЗС', 'сексол.', 'сельск.', 'сельхоз.', 'семантика', 'Серов', 'синонимы',
    'синонимы:мало', 'синонимы:много', 'Скляревская 2006', 'скр1', 'скр2', 'скрыто', 'Слайдер', 'сленг', 'сленг.',
    'СЛИН', 'слобр', 'слово дня', 'словоформа', 'слря11-17', 'слря18', 'слэнг', 'см-70', 'см-77', 'см-82', 'см-83',
    'смягчит.', 'сниж.', 'СНС 50-80', 'СНСРЯ', 'собир.', 'собират.', 'сов.', 'Совдепия', 'совет.', 'советск.', 'сокр.',
    'Солженицын', 'соотн.', 'СОРЯА', 'состояние', 'социол.', 'спелеол.', 'спец.', 'списки семантических связей',
    'спорт.', 'ср.', 'СРНГ', 'СРНГ-2', 'СРРЭ', 'СРФ', 'СРЯ 11-17', 'СРЯ 18', 'ССРЛЯ', 'ссылки с пометой', 'ссылки',
    'старин.', 'стат.', 'статив.', 'статья', 'стекловарн.', 'стол.', 'столярн.', 'стомат.', 'СТРА', 'строит.',
    'студ. жарг.', 'студ.', 'студ.жарг.', 'субст.', 'субстантив.', 'субстантивир.', 'Суперанская-СГН', 'сх', 'сэ', 'ся',
    'табу', 'театр.', 'текст.', 'телеком.', 'Телия', 'термин', 'тех.', 'техн. жарг.', 'техн.', 'техн.жарг.', 'тж.',
    'типогр.', 'Тихонов', 'ТЛБ', 'Толль', 'торг.', 'торж.', 'трад.-нар.', 'трад.-поэт.', 'тракторн.', 'транс.',
    'трансп.', 'тс', 'ТСД', 'ТСРРР', 'ТСРРЯ', 'ТСРЯЭ', 'ТССЕРЯ', 'уважит.', 'увелич.', 'увеличит.', 'уг. жарг.',
    'угол.', 'укр.', 'ум.-ласк.', 'уменьш.', 'умласк', 'умласк.', 'Унбегаун', 'унич.', 'уничиж.', 'управл.', 'усилит.',
    'уст.', 'устар.', 'Участник:Vitalik7/Песочница/проверка включения длины слова', 'Ушаков', 'Ушаков1940', 'Ф', 'фам.',
    'фант.', 'фарм.', 'Фасмер', 'физ.', 'физиол.', 'филат.', 'филол.', 'филос.', 'фин.', 'фобия', 'фолькл.', 'фото',
    'фотогр.', 'Фразеологизмы', 'Фразеологический словарь Молоткова, 1987', 'ФСРЛЯ', 'хим-элем', 'хим.', 'хоз.',
    'хореогр.', 'худ.пр.', 'худож.', 'ц.-слав.', 'цвет', 'ценз', 'ценз2', 'церк.', 'церк.-сл.', 'церк.-слав.', 'цирк.',
    'цитол.', 'цы', 'Цыганенко', 'через', 'через2', 'Черных', 'числ.', 'Шагалова 2017', 'Шагалова', 'Шагалова2012',
    'Шанский', 'Шапошников', 'шахм.', 'Шахматная диаграмма', 'шашечн.', 'швейн.', 'Шипова', 'школьн.', 'шутл.',
    'э:cu:градъ', 'э:orv:громъ', 'э:orv:сахаръ', 'эвф.', 'экзот.', 'экол.', 'экон.', 'эконом.', 'экспр.', 'экспресс.',
    'эл.-техн.', 'эл.-энерг.', 'электр.', 'энтом.', 'энтомол.', 'эррат.', 'ЭСБЕ', 'ЭСРЯ МГУ', 'ЭССЯ2', 'этимология',
    'этимология:', 'этимология:варроатоз', 'этимология:вода', 'этимология:Ярило', 'этногр.', 'этнол.', 'этнолог.',
    'ювел.', 'юр.', 'юрид.', 'ЯИ', 'ЯН', 'ЯРГ',
    'Форма-мест', 'форма-гл', 'форма-прил', 'форма-сущ', 'Форма-числ', 'форма-прич','эзот.', 'тех.жарг.',
}

double_title_case(ignore_templates)
