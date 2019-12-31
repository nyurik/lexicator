from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Set, Union, Any

__all__ = ["mono_value", "ClaimValue", "set_qualifiers_on_new", "set_references_on_new", "Property",
           "P_HAS_QUALITY", "P_GRAMMATICAL_GENDER", "P_INFLECTION_CLASS", "P_WORD_STEM", "P_WORD_ROOT",
           "P_PRONUNCIATION", "P_IPA_TRANSCRIPTION", "P_PRONUNCIATION_AUDIO", "P_HYPHENATION", "P_DESCRIBED_BY",
           "P_IMPORTED_FROM_WM"]


def mono_value(lang, text):
    return {'text': text, 'language': lang}


@dataclass
class ClaimValue:
    value: Union[str, Dict]
    qualifiers: Dict[Property, Set[str]] = field(default_factory=dict)
    rank: str = 'normal'

    def __post_init__(self):
        if not self.value:
            raise ValueError('Claim value cannot be empty')


def set_qualifiers_on_new(claim, qualifiers: Dict[Property, Any]):
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


def set_references_on_new(claim, references: Dict[Property, Any]):
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
    ALL: Dict[str, Property] = {}

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

    def __eq__(self, o: Property) -> bool:
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
