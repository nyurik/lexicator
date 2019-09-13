from typing import Dict, Set, Union, List, Any
from dataclasses import dataclass, field


def mono_value(lang, text):
    return {'text': text, 'language': lang}


@dataclass
class ClaimValue:
    value: Union[str, Dict]
    qualifiers: Dict['Property', Set[str]] = field(default_factory=dict)
    rank: str = 'normal'


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


def set_refernces_on_new(claim, references: Dict['Property', Any]):
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

    def __init__(self, id, name, type, allow_multiple=False, allow_qualifiers=False, is_qualifier=False, ignore=False,
                 merge_all=False):
        self.ignore = ignore
        self.id = id
        self.name = name
        self.type = type
        self.merge_all = merge_all
        self.allow_multiple = allow_multiple
        self.allow_qualifiers = allow_qualifiers
        self.is_qualifier = is_qualifier
        self.is_item = type == 'wikibase-item'
        self.is_monotext = type == 'monolingualtext'
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
        if 'claims' not in data: data['claims'] = {}
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
        if allow_multiple is None: allow_multiple = self.allow_multiple
        if allow_qualifiers is None: allow_qualifiers = self.allow_qualifiers
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
}

Q_ZAL_ADJ_CLASSES = {
    '1a': 'Q67397478',
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

zal_normalizations = {
    '(с3*a(1))': '(с3*a①)',
    '(с3a(1))': '(с3a①)',
    '(с4a(1))': '(с4a①)',
    '(с6a(2))': '(c6a②)',
    '1°c(1)': '1°c①',
    '1a((1))': '1a[①]',
    '1a((2))': '1a[②]',
    '1a(2)': '1a②',
    '1a(2)^': '1a②^',
    '1b(1)': '1b①',
    '1c(1)': '1c①',
    '1c(1)^': '1c①^',
    '1c(1)(2)': '1c①②',
    '1c(2)': '1c②',
    '1e(2)': '1e②',
    '2*a(2)': '2*a②',
    '2a(2)': '2a②',
    '2b(1)': '2b①',
    '2c(1)': '2c①',
    '2f(2)': '2f②',
    '3*a(1)': '3*a①',
    '3*a(1)(2)': '3*a①②',
    '3*a(2)': '3*a②',
    '3*b(1)': '3*b①',
    '3*b(1)(2)': '3*b①②',
    '3*b(2)': '3*b②',
    '3*c(2)': '3*c②',
    '3*d(2)': '3*d②',
    '3a(1)': '3a①',
    '3a(1)(2)': '3a①②',
    '3b(1)': '3b①',
    '3c(1)': '3c①',
    '3c(2)': '3c②',
    '3d(1)': '3d①',
    '4a(1)': '4a①',
    '4a(2)': '4a②',
    '4c(1)': '4c①',
    '4f(1)': '4f①',
    '5*a((2))': '5*a[②]',
    '5*a(2)': '5*a②',
    '5*b(2)': '5*b②',
    '5a(2)': '5a②',
    '6*a((2))': '6*a[②]',
    '6*a(2)': '6*a②',
    '6*d(2)': '6*d②',
    '6c(1)': '6c①',
    '7a(3)': '7a③',
    '7b(2)': '7b②',
    '7c(3)': '7c③',
}

# '*' :'Q66624434',
# '°' :'Q66619529',
# '(1)' :'Q66624528', # ①
# '(2)' :'Q66624537', # ②
# '(3)' :'Q66624544', # ③
# '—' :'Q66624618',

# Stem Classes
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

# CREATE
# LAST	Lru	"класс 1*a по Зализняку"
# LAST	Dru	"класс существительного 1*a согласно классификации Зализняка"
# LAST	Len	"class 1*a in Zaliznyak"
# LAST	Den	"noun class 1*a in Zaliznyak classification"
# LAST	P31	Q66329814
# LAST	P407	Q7737
# LAST	P1552	Q66605819
# LAST	P1552	Q66459699
# LAST	P1552	Q66624434
