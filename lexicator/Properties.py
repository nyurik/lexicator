from dataclasses import dataclass, field
from typing import Dict, Set, Union, Any


def mono_value(lang, text):
    return {'text': text, 'language': lang}


@dataclass
class ClaimValue:
    value: Union[str, Dict]
    qualifiers: Dict['Property', Set[str]] = field(default_factory=dict)
    rank: str = 'normal'

    def __post_init__(self):
        if not self.value:
            raise ValueError('Claim value cannot be empty')


def set_qualifiers_on_new(claim, qualifiers: Dict['Property', Any]):
    if qualifiers and len(qualifiers) > 0:
        try:
            q = claim['qualifiers']
        except KeyError:
            q = {}
            claim['qualifiers'] = q
        for p, vals in qualifiers.items():
            if isinstance(vals, str):
                vals = [vals]
            q[p.id] = [p.create_snak(v) for v in vals]


def set_references_on_new(claim, references: Dict['Property', Any]):
    if references and len(references) > 0:
        try:
            ref = claim['references']
        except KeyError:
            ref = [dict(snaks={})]
            claim['references'] = ref
        ref = ref[0]['snaks']
        for p, vals in references.items():
            if isinstance(vals, str):
                vals = [vals]
            ref[p.id] = [p.create_snak(v) for v in vals]


class Property:
    ALL: Dict[str, 'Property'] = {}

    def __init__(self, pid, name, typ, allow_multiple=False, allow_qualifiers=False, is_qualifier=False, ignore=False,
                 merge_all=False):
        self.ignore = ignore
        self.id = pid
        self.name = name
        self.type = typ
        self.merge_all = merge_all
        self.allow_multiple = allow_multiple
        self.allow_qualifiers = allow_qualifiers
        self.is_qualifier = is_qualifier
        self.is_item = typ == 'wikibase-item'
        self.is_monotext = typ == 'monolingualtext'
        if self.is_item:
            self.dv_type = 'wikibase-entityid'
        elif self.is_monotext:
            self.dv_type = 'monolingualtext'
        else:
            self.dv_type = 'string'
        if self.id in Property.ALL:
            raise ValueError(f'{self.id} already exists for {Property.ALL[self.id]}')
        Property.ALL[self.id] = self

    def __str__(self):
        return self.__repr__()

    def __repr__(self):
        return f'{self.name} ({self.id})'

    def __hash__(self) -> int:
        return self.id.__hash__()

    def __eq__(self, o: 'Property') -> bool:
        return self.id.__eq__(o.id)

    def create_snak(self, value):
        if self.is_item:
            value = {'entity-type': 'item', 'id': value}
        elif self.is_monotext:
            # if isinstance(value, tuple) and len(value) == 2:
            #     value = mono_value(value[0], value[1])
            # el
            if not isinstance(value, dict) or len(value) != 2:
                raise ValueError('Monolingual values expect a two value tuple or a lang/text dict')

        return {
            'snaktype': 'value',
            'property': self.id,
            # 'datatype': self.type,
            'datavalue': {
                'value': value,
                'type': self.dv_type,
            }
        }

    def remove_claim(self, data, value: ClaimValue):
        if 'claims' not in data or self.id not in data['claims']:
            return
        claims = data['claims'][self.id]
        for claim in claims:
            if self.claim_to_claimvalue(claim, True) == value:
                claims.remove(claim)
                if not claims:
                    del data['claims'][self.id]
                break

    def set_claim_on_new(self, data, value: ClaimValue):
        if 'claims' not in data:
            data['claims'] = {}
        claims = data['claims']
        claim = {
            'mainsnak': self.create_snak(value.value),
            'type': 'statement',
            'rank': value.rank,
        }
        set_qualifiers_on_new(claim, value.qualifiers)

        if self.id in claims:
            if not self.merge_all and not self.allow_multiple and not self.allow_qualifiers:
                raise ValueError(
                    f"Cannot set value of {self} to '{value}', "
                    f"already set to '{self.get_value(data['claims'][self.id][0])}'")
            claims[self.id].append(claim)
        else:
            claims[self.id] = [claim]

    def get_value(self, item):
        if 'mainsnak' in item:
            if item['type'] != 'statement':
                raise ValueError(f'Unknown mainsnak type "{item["type"]}"')
            item = item['mainsnak']
        if 'datavalue' in item:
            if item['snaktype'] != 'value':
                raise ValueError(f'Unknown snaktype "{item["snaktype"]}"')
            dv = item['datavalue']
            if dv['type'] != self.dv_type:
                raise ValueError(f'Datavalue type "{dv["type"]}" should be "{self.dv_type}"')
            value = dv['value']
            if self.is_item:
                if not isinstance(value, dict):
                    raise ValueError(f'Unexpected type "{type(value)}", should be "dict"')
                if value['entity-type'] != 'item':
                    raise ValueError(f'wd item type "{value["entity-type"]}" should be "item"')
                return value['id']
            # elif self.is_monotext:
            #     return value['language'], value['text']
            return value
        raise ValueError('Unexpected item')

    def get_claim_value(self, item, allow_multiple=None, allow_qualifiers=None):
        if allow_multiple is None:
            allow_multiple = self.allow_multiple
        if allow_qualifiers is None:
            allow_qualifiers = self.allow_qualifiers
        if 'claims' in item and self.id in item.claims:
            claims = item.claims[self.id]
        elif self.id in item:
            # parsing qualifier
            claims = item[self.id]
        else:
            return None
        if len(claims) > 1 and not allow_multiple:
            raise ValueError(f"Item {item.id} has {len(claims)} claims {self}")
        values = []
        for claim in claims:
            values.append(self.claim_to_claimvalue(claim, allow_qualifiers))
        if not allow_multiple:
            return values[0]
        else:
            return values

    def claim_to_claimvalue(self, claim, include_qualifiers):
        value = self.get_value(claim)
        if include_qualifiers:
            qualifiers = {}
            if 'qualifiers' in claim:
                for qid, qval in claim.qualifiers.items():
                    qprop = Property.ALL[qid]
                    qlf = qprop.get_claim_value(claim.qualifiers)
                    if qlf:
                        qualifiers[qprop] = qlf if qprop.is_monotext else set(qlf)
            value = ClaimValue(value, qualifiers, claim.rank)
        elif 'qualifiers' in claim:
            raise ValueError(f'{self} does not support qualifiers')
        return value

    def value_from_claim(self, claim):
        if self.is_item:
            return claim.target.id
        if self.type == 'commonsMedia':
            return claim.target.titleWithoutNamespace()
        return claim.target


# Statements
P_HAS_QUALITY = Property('P1552', 'has-quality', 'wikibase-item', allow_multiple=True)
P_GRAMMATICAL_GENDER = Property('P5185', 'grammatical-gender', 'wikibase-item')
P_INFLECTION_CLASS = Property('P5911', 'inflection-class', 'wikibase-item', allow_multiple=True)
P_WORD_STEM = Property('P5187', 'word-stem', 'monolingualtext', allow_multiple=True)
P_WORD_ROOT = Property('P5920', 'word-root', 'wikibase-item', allow_multiple=True)

# Forms
P_PRONUNCIATION = Property('P7243', 'pronunciation', 'monolingualtext', allow_qualifiers=True)
P_IPA_TRANSCRIPTION = Property('P898', 'IPA-transcription', 'string', is_qualifier=True)
P_PRONUNCIATION_AUDIO = Property('P443', 'pronunciation-audio', 'commonsMedia', is_qualifier=True)
P_HYPHENATION = Property('P5279', 'hyphenation', 'string')

P_DESCRIBED_BY = Property('P1343', 'described-by', 'wikibase-item')

P_IMPORTED_FROM_WM = Property('P143', 'imported-from-wm', 'wikibase-item', is_qualifier=True)
Q_RU_WIKTIONARY = 'Q22116890'

Q_RUSSIAN_LANG = 'Q7737'
RUSSIAN_PRE_REFORM_ID = 'ru-x-Q2442696'

Q_SOURCES = {
    'оэсря': 'Q67130942',
}

# SELECT ?idLabel ?id WHERE {
#   ?id wdt:P31 wd:Q82042.
#   SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
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

Q_ZAL_ADJ_CLASSES = {
    "(мс 6*a)": "Q67537172",
    "0": "Q67537176",
    "1*a": "Q66821141",
    "1*a'": "Q67537179",
    "1*a'-": "Q67537183",
    "1*a'②": "Q67537185",
    "1*a(①)": "Q67537186",
    "1*a-": "Q67537189",
    "1*a/b": "Q67537193",
    "1*a/b~": "Q67537194",
    "1*a/b②": "Q67537198",
    "1*a/c": "Q67537201",
    "1*a/c'": "Q67537204",
    "1*a/c'~": "Q67537208",
    "1*a/c\"": "Q67537444",
    "1*aX": "Q67537210",
    "1*a~": "Q67537212",
    "1*a①": "Q67537214",
    "1*a①-": "Q67537216",
    "1*a②": "Q67537218",
    "1*b": "Q67537221",
    "1*b/c'": "Q67537223",
    "1*b/c\"": "Q67537447",
    "1*b^": "Q67537224",
    "1a": "Q67397478",
    "1a'": "Q67537229",
    "1a'~": "Q67537232",
    "1a-": "Q67537233",
    "1a/b": "Q67537237",
    "1a/c": "Q67537239",
    "1a/c'": "Q67537241",
    "1a/c'~": "Q67537244",
    "1a/c-ё": "Q67537246",
    "1a/c\"": "Q67537450",
    "1a/c~": "Q67537248",
    "1a?": "Q67537250",
    "1a?10": "Q67537253",
    "1a?7": "Q67537254",
    "1a^": "Q67537255",
    "1b": "Q67537259",
    "1b/c": "Q67537261",
    "1b/c'": "Q67537264",
    "1b/c'~": "Q67537268",
    "1b/c~": "Q67537270",
    "1b/c~^": "Q67537271",
    "1b?": "Q67537275",
    "1bX": "Q67537278",
    "2*a": "Q67537279",
    "2*a-": "Q67537281",
    "2*a^": "Q67537284",
    "2a": "Q67537286",
    "2a/c": "Q67537288",
    "3*a": "Q67537289",
    "3*a'": "Q67537293",
    "3*a/b": "Q67537295",
    "3*a/c": "Q67537299",
    "3*a/c'": "Q67537300",
    "3*a/c'^-к": "Q67537302",
    "3*a/c\"": "Q67537453",
    "3*a/c^": "Q67537304",
    "3*aX~": "Q67537307",
    "3*a~": "Q67537309",
    "3a": "Q67537311",
    "3a'": "Q67537314",
    "3a'~": "Q67537317",
    "3a/b~": "Q67537319",
    "3a/c": "Q67537321",
    "3a/c'": "Q67537327",
    "3a/c\"": "Q67537456",
    "3a/c\"~": "Q67537324",
    "3a^": "Q67537330",
    "3a^+": "Q67537332",
    "3aX~": "Q67537334",
    "3a~": "Q67537338",
    "3b": "Q67537342",
    "3b-нибудь": "Q67537344",
    "3b/c": "Q67537347",
    "3b/c'": "Q67537350",
    "3b/c'~": "Q67537353",
    "3b/c~": "Q67537356",
    "3bX~": "Q67537359",
    "4a": "Q67537362",
    "4a-ся": "Q67537364",
    "4a/b": "Q67537369",
    "4a/b'": "Q67537371",
    "4a/b~": "Q67537373",
    "4a/c": "Q67537376",
    "4aX": "Q67537378",
    "4aX~": "Q67537381",
    "4b": "Q67537382",
    "4bX": "Q67537384",
    "4b~^": "Q67537386",
    "5a": "Q67537389",
    "6a": "Q67537392",
}

Q_ZAL_NOUN_CLASSES = {
    '0': 'Q66712697',
    '1*a': 'Q66716618',
    '1a': 'Q66311515',
    '1b': 'Q66606159',
    '1c': 'Q66606177',
    '1c①': 'Q66716619',
    '1d': 'Q66606179',
    '1e': 'Q66606180',
    '1f': 'Q66606181',
    '1°a': 'Q66716620',
    '2*a': 'Q66716622',
    '2a': 'Q66606182',
    '2b': 'Q66606183',
    '2c': 'Q66606184',
    '2d': 'Q66606185',
    '2e': 'Q66606186',
    '2f': 'Q66606187',
    '3*a': 'Q66716624',
    '3*b': 'Q66716625',
    '3a': 'Q66606188',
    '3b': 'Q66606189',
    '3c': 'Q66606190',
    '3d': 'Q66606191',
    '3e': 'Q66606192',
    '3°a': 'Q66716627',
    '4a': 'Q66606193',
    '4b': 'Q66606194',
    '4c': 'Q66606195',
    '5*a': 'Q66716628',
    '5*b': 'Q66716629',
    '5a': 'Q66606196',
    '5b': 'Q66606197',
    '6*a': 'Q66716630',
    '6*b': 'Q66716631',
    '6a': 'Q66606198',
    '6b': 'Q66606199',
    '6c': 'Q66606200',
    '7a': 'Q66327520',
    '8a': 'Q66606201',
    '8b': 'Q66606202',
    '8e': 'Q66606203',
}

# '*' :'Q66624434',
# '°' :'Q66619529',
# '(1)' :'Q66624528', # ①
# '(2)' :'Q66624537', # ②
# '(3)' :'Q66624544', # ③
# '—' :'Q66624618',

# Noun Stem Classes
# 0	Q66691574
# 1	Q66605819
# 2	Q66311616
# 3	Q66312026
# 4	Q66312029
# 5	Q66312036
# 6	Q66312041
# 7	Q66312044
# 8	Q66312049

# Stress Classes
# a	Q66459699
# b	Q66605860
# b′	Q66689132
# c	Q66605863
# d	Q66605874
# d′	Q66689125
# e	Q66605877
# f	Q66605882
# f′	Q66689116
# f′′	Q66689120

# Adj Stem Classes
# 0 Q67534715
# 1 Q66821144
# 2 Q67534719
# 3 Q67534720
# 4 Q67534722
# 5 Q67534724
# 6 Q67534727

# CREATE
# LAST	Lru	"класс адъективного склонения 1*a по Зализняку"
# LAST	Dru	"класс адъективного склонения 1*a согласно классификации Зализняка"
# LAST	Len	"adj declension class 1*a in Zaliznyak"
# LAST	Den	"adjective declension class 1*a in Zaliznyak classification"
# LAST	P31	Q66821148
# LAST	P407	Q7737
# LAST	P1552	Q66605819
# LAST	P1552	Q66459699
# LAST	P1552	Q66624434
