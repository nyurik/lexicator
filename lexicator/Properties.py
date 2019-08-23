from typing import Dict, Set, Union
from dataclasses import dataclass, field


def mono_value(lang, text):
    return {'language': lang, 'text': text}


@dataclass
class ClaimValue:
    value: Union[str, Dict]
    qualifiers: Dict['Property', Set[str]] = field(default_factory=dict)
    rank: str = 'normal'


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
            'datatype': self.type,
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
            'type': 'statement',
            'rank': value.rank,
            'mainsnak': self.create_snak(value.value),
        }
        if value.qualifiers and len(value.qualifiers) > 0:
            claim['qualifiers'] = {}
            for p, vals in value.qualifiers.items():
                claim['qualifiers'][p.id] = [p.create_snak(v) for v in vals]

        if self.id in claims:
            if not self.merge_all and not self.allow_multiple and not self.allow_qualifiers:
                raise ValueError(
                    f"Cannot set value of {self} to '{value}', "
                    f"already set to '{self.get_value(data['claims'][self])}'")
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

# Forms
P_IPA_TRANSCRIPTION = Property('P898', 'IPA-transcription', 'string')
P_PRONUNCIATION_AUDIO = Property('P443', 'pronunciation-audio', 'commonsMedia')
P_HYPHENATION = Property('P5279', 'hyphenation', 'string')

Q_RUSSIAN_LANG = 'Q7737'

# SELECT ?idLabel ?id WHERE {
#   ?id wdt:P31 wd:Q82042.
#   SERVICE wikibase:label { bd:serviceParam wikibase:language "[AUTO_LANGUAGE],en". }
Q_PART_OF_SPEECH = {
    'noun': 'Q1084',
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
}

Q_FEATURES = {
    # Numbers
    'singular': 'Q110786',
    'plural': 'Q146786',

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
}

Q_GENDERS = {
    'feminine': 'Q1775415',
    'masculine': 'Q499327',
    'neuter': 'Q1775461',  # средний род
    'common': 'Q1305037',  # общий род
}

Q_QUALITIES = {
    'animate': 'Q51927507',  # одушевлённое
    'inanimate': 'Q51927539',  # неодушевлённое
}

Q_DECLENSIONS = {  # склонения
    '1': 'Q66327367',
    '2': 'Q66689134',
    '3': 'Q66689140',
    'indeclinable noun': 'Q66689173',
    'adjectival': 'Q66689191',
    'pronoun': 'Q66689198',
}

Q_ZEL_CLASSES = {
    '1a': 'Q66311515',
    '1b': 'Q66606159',
    '1c': 'Q66606177',
    '1d': 'Q66606179',
    '1e': 'Q66606180',
    '1f': 'Q66606181',
    '2a': 'Q66606182',
    '2b': 'Q66606183',
    '2c': 'Q66606184',
    '2d': 'Q66606185',
    '2e': 'Q66606186',
    '2f': 'Q66606187',
    '3a': 'Q66606188',
    '3b': 'Q66606189',
    '3c': 'Q66606190',
    '3d': 'Q66606191',
    '3e': 'Q66606192',
    '4a': 'Q66606193',
    '4b': 'Q66606194',
    '4c': 'Q66606195',
    '5a': 'Q66606196',
    '5b': 'Q66606197',
    '6a': 'Q66606198',
    '6b': 'Q66606199',
    '6c': 'Q66606200',
    '7a': 'Q66327520',
    '8a': 'Q66606201',
    '8b': 'Q66606202',
    '8e': 'Q66606203',
}
