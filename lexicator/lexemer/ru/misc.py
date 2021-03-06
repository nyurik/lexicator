from __future__ import annotations

from typing import Callable

from lexicator.consts.ru import RUSSIAN_PRE_REFORM_ID, remove_stress
from ..Properties import *
from ..TemplateProcessor import TemplateProcessor, TemplateProcessorBase
from ..TemplateUtils import test_str


def assert_lang(param_getter, expects_lang):
    lang = param_getter('lang')
    if lang and lang != expects_lang:
        raise ValueError(f"Unexpected lang={lang}")


class RuTranscription(TemplateProcessor):
    def __init__(self, lang_code: str, template: str) -> None:
        super().__init__(lang_code, template, ['1', '2', 'lang', 'источник', 'норма'])

    # noinspection PyUnusedLocal
    def run(self, parser, param_getter: Callable[[str], str], params: dict):
        assert_lang(param_getter, 'ru')
        index = self.get_index(parser)
        parser.set_pronunciation_qualifier(
            index, parser.primary_form, P_PRONUNCIATION_AUDIO, param_getter('2'), parser.validate_file)
        parser.set_pronunciation_qualifier(
            index, parser.primary_form, P_IPA_TRANSCRIPTION, param_getter('1'), parser.validate_ipa)

        parser.set_pronunciation_reference(index, parser.primary_form, param_getter('источник'))

        param_getter('норма')  # ignore


class RuTranscriptions(TemplateProcessor):
    def __init__(self, lang_code: str, template: str) -> None:
        super().__init__(lang_code, template, ['1', '2', '3', '4', 'мн2', 'lang', 'источник', 'норма'])

    # noinspection PyUnusedLocal
    def run(self, parser, param_getter: Callable[[str], str], params: dict):
        assert_lang(param_getter, 'ru')
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


class RuHyphenation(TemplateProcessorBase):
    # Parses {'1': 'а́', '2': '.', '3': 'ист'}, ignores '.', does some validation
    def process(self, parser, params):
        parts = [params[str(v)] for v in sorted(
            (v for v in params.keys() if v != 'коммент'),
            key=lambda k: int(k))]

        new_parts = []
        merge_next = False
        for idx, part in enumerate(parts):
            if part == '.':
                if (idx != 1 and idx != len(parts) - 2) or merge_next:
                    print(f'{parser.title}: unexpected non-breaking syllable position {idx} in {parts}')
                merge_next = True
            else:
                # FIXME: is this the right spelling, or should it be "hyphenation" ?
                part = parser.validate_str(part, 'hypenation')
                if merge_next:
                    new_parts[-1] += part
                    merge_next = False
                else:
                    new_parts.append(part)

        new_value = remove_stress('‧'.join(new_parts))
        try:
            form_obj = parser.form_by_param[parser.primary_form]
        except KeyError:
            raise ValueError(f"primary form '{parser.primary_form}' has not yet been created. "
                             f"Existing forms: [{', '.join(parser.form_by_param.keys())}]")
        P_HYPHENATION.set_claim_on_new(form_obj, ClaimValue(new_value))


class RuPreReformSpelling(TemplateProcessorBase):
    def process(self, parser, params):
        form = parser.form_by_param[parser.primary_form]
        if RUSSIAN_PRE_REFORM_ID in form['representations']:
            raise ValueError(
                f"{RUSSIAN_PRE_REFORM_ID} is already set on {form}. "
                f"Old={form['representations'][RUSSIAN_PRE_REFORM_ID]['value']}, new={params}")
        form['representations'][RUSSIAN_PRE_REFORM_ID] = {
            'language': RUSSIAN_PRE_REFORM_ID,
            'value': test_str(params, RUSSIAN_PRE_REFORM_ID)
        }
