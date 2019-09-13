from typing import Callable

from lexicator.TemplateUtils import test_str
from lexicator.consts import re_russian_word
from lexicator.utils import remove_stress
from .TemplateProcessor import TemplateProcessor, TemplateProcessorBase
from .Properties import *


def assert_lang(param_getter):
    lang = param_getter('lang')
    if lang and lang != 'ru':
        raise ValueError(f"Unexpected lang={lang}")


class TranscriptionRu(TemplateProcessor):
    def __init__(self, template: str) -> None:
        super().__init__(template, ['1', '2', 'lang', 'источник', 'норма'])

    def run(self, parser, param_getter: Callable[[str], str], params: dict):
        assert_lang(param_getter)
        index = self.get_index(parser)
        parser.set_pronunciation_qualifier(
            index, parser.primary_form, P_PRONUNCIATION_AUDIO, param_getter('2'), parser.validate_file)
        parser.set_pronunciation_qualifier(
            index, parser.primary_form, P_IPA_TRANSCRIPTION, param_getter('1'), parser.validate_ipa)

        parser.set_pronunciation_reference(index, parser.primary_form, param_getter('источник'))

        param_getter('норма')  # ignore


class TranscriptionsRu(TemplateProcessor):
    def __init__(self, template: str) -> None:
        super().__init__(template, ['1', '2', '3', '4', 'мн2', 'lang', 'источник', 'норма'])

    def run(self, parser, param_getter: Callable[[str], str], params: dict):
        assert_lang(param_getter)
        index = self.get_index(parser)

        parser.set_pronunciation_qualifier(
            index, parser.primary_form, P_PRONUNCIATION_AUDIO, param_getter('3'), parser.validate_file)
        parser.set_pronunciation_qualifier(
            index, parser.primary_form, P_IPA_TRANSCRIPTION, param_getter('1'), parser.validate_ipa)
        parser.set_pronunciation_qualifier(
            index, 'nom-pl', P_PRONUNCIATION_AUDIO, param_getter('4'), parser.validate_file)
        parser.set_pronunciation_qualifier(
            index, 'nom-pl', P_IPA_TRANSCRIPTION, param_getter('2'), parser.validate_ipa)
        parser.set_pronunciation_qualifier(
            index, 'nom-pl2', P_IPA_TRANSCRIPTION, param_getter('мн2'), parser.validate_ipa)

        parser.set_pronunciation_reference(index, parser.primary_form, param_getter('источник'))

        param_getter('норма')  # ignore


class Hyphenation(TemplateProcessorBase):
    # Parses {'1': 'а́', '2': '.', '3': 'ист'}, ignores '.', does some validation
    def process(self, parser, params):
        parts = [params[str(v)] for v in sorted(params.keys(), key=lambda k: int(k))]

        new_parts = []
        merge_next = False
        for idx, part in enumerate(parts):
            if part == '.':
                if (idx != 1 and idx != len(parts) - 2) or merge_next:
                    print(f'{parser.title}: unexpected non-breaking syllable position {idx} in {parts}')
                merge_next = True
            else:
                if not re_russian_word.match(part):
                    raise ValueError(f'syllable "{part}" does not seem to be a russian word')
                if merge_next:
                    new_parts[-1] += part
                    merge_next = False
                else:
                    new_parts.append(part)

        new_value = remove_stress('‧'.join(new_parts))
        P_HYPHENATION.set_claim_on_new(
            parser.form_by_param[parser.primary_form],
            ClaimValue(new_value))


class PreReformSpelling(TemplateProcessorBase):
    def process(self, parser, params):
        form = parser.form_by_param[parser.primary_form]
        if RUSSIAN_PRE_REFORM_ID in form['representations']:
            raise ValueError(
                f"{RUSSIAN_PRE_REFORM_ID} is already set on {form}. "
                f"Old={form['representations'][RUSSIAN_PRE_REFORM_ID]['value']}, new={params}")
        form['representations'][RUSSIAN_PRE_REFORM_ID] = {
            'language': RUSSIAN_PRE_REFORM_ID,
            'value': test_str(params)
        }
