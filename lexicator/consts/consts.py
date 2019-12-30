import re

re_file = re.compile(r'^[^<>]+\.(ogg|wav|mp3)$')

# From http://www.internationalphoneticalphabet.org/ipa-charts/ipa-symbols-with-unicode-decimal-and-hex-codes/
# noinspection SpellCheckingInspection
IPA_SYMBOLS = '‿⁽⁾()abcdefghijklmnopqrstuvwxyzɑɐɒæɓʙβɔɕçɗɖðʤəɘɚɛɜɝɞɟʄɡɠɢʛɦɧħɥʜɨɪʝɭɬɫɮʟɱɯɰŋɳɲɴøɵɸθœɶʘɹɺɾɻʀʁɽʂʃʈʧ' \
              'ʉʊʋⱱʌɣɤʍχʎʏʑʐʒʔʡʕʢǀǁǂǃˈˌːˑʼʴʰʱʲʷˠˤ˞ɫ↓↑→↗↘\u0325\u030A\u0324\u032A\u032C\u0330\u033A\u033C\u033B' \
              '\u031A\u0339\u0303\u031C\u031F\u0320\u0308\u0334\u033D\u031D\u0329\u031E\u032F\u0318\u0319\u0306' \
              '\u030B\u0301\u0304\u0300\u030F\u035C\u0361'

word_types_IPA = {
    'letters only': re.compile(rf'^[{IPA_SYMBOLS}]+$'),
    # Add space as an allowed symbol
    'multi-word dash-separated': re.compile(rf'^[ {IPA_SYMBOLS}]+$'),
    'multi-word space-separated': re.compile(rf'^[ {IPA_SYMBOLS}]+$'),
}

NS_MAIN = 0
NS_USER = 2
NS_USER_TALK = 3
NS_TEMPLATE = 10
NS_TEMPLATE_TALK = 11
NS_LEXEME = 146

# SELECT ?idLabel ?id WHERE {
#   ?id wdt:P31 wd:Q82042.
#   SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }

# noinspection SpellCheckingInspection
Q_PART_OF_SPEECH = {
    'noun': 'Q1084',
    'common noun': 'Q2428747',
    'participle': 'Q814722',
    'possessive adjective': 'Q5051',
    'verb': 'Q24905',
    'adjective': 'Q34698',
    'pronoun': 'Q36224',
    'conjunction': 'Q36484',
    'numeral': 'Q63116',
    'interjection': 'Q83034',
    'article': 'Q103184',
    'adposition': 'Q134316',
    'postposition': 'Q161873',
    'grammatical particle': 'Q184943',
    'adjektivadverb': 'Q357750',
    'circumposition': 'Q358417',
    'adverb': 'Q380057',
    'determiner': 'Q576271',
    'transgressive': 'Q904896',
    'relative pronoun': 'Q1050744',
    'adjectival noun': 'Q1091269',
    'possessive pronoun': 'Q1502460',
    'parenthesis': 'Q1930668',
    'pro-form': 'Q2006180',
    'pro-verb': 'Q2628203',
    'demonstrative adjective': 'Q2824480',
    'exophora': 'Q3851383',
    'preposition': 'Q4833830',
    'adnominal adjective': 'Q11639843',
    'limiter': 'Q12252798',
    'relative adverb': 'Q15107093',
    'quantitative': 'Q21087400',
    'coordinating conjunction': 'Q28833099',
    'demonstrative pronoun': 'Q34793275',
    'interrogative pronoun': 'Q54310231',
    'quantitative adverb': 'Q55869214',
    'qualitative pronoun': 'Q62059381',
    'comparative adverb': 'Q65248385',
    'onomatopoeia': 'Q170239',
}

Q_FEATURES = {
    # Numbers
    'singular': 'Q110786',
    'plural': 'Q146786',
    'rare-form': 'Q55094451',

    # Cases
    'nominative': 'Q131105',  # именительный
    'genitive': 'Q146233',  # родительный
    'dative': 'Q145599',  # дательный
    'accusative': 'Q146078',  # винительный
    'instrumental': 'Q192997',  # творительный
    'prepositional': 'Q2114906',  # предложный
    'locative': 'Q202142',  # местный
    'vocative': 'Q185077',  # звательный
    'partitive': 'Q857325',  # разделительный
    'possessive': 'Q21470140',  # притяжательный

    # Special for Adjective
    'short-form-adjective': 'Q4239848',

    # Genders
    'feminine': 'Q1775415',
    'masculine': 'Q499327',
    'neuter': 'Q1775461',  # средний род
    'common': 'Q1305037',  # общий род

    # Qualities
    'animate': 'Q51927507',  # одушевлённое
    'inanimate': 'Q51927539',  # неодушевлённое

    # Declensions -- склонения
    'declension-1': 'Q66327367',
    'declension-2': 'Q66689134',
    'declension-3': 'Q66689140',
    'indeclinable noun': 'Q66689173',
    'adjectival': 'Q66689191',
    'pronoun': 'Q66689198',

    # aspects -- вид
    'imperfective aspect': 'Q371427',  # несовершенный вид
    'perfective aspect': 'Q1424306',  # совершенный вид

    # voice -- залог
    'active voice': 'Q131783109',  # действительный залог
    'passive voice': 'Q1194697',  # страдательный залог
    'reflexive voice': 'Q63615081',  # возвратный залог

    # tense -- время
    'past tense': 'Q1994301',  # прошедшего времени
    'present tense': 'Q192613',  # настоящего времени
    'future tense': 'Q501405',  # настоящего времени
}
