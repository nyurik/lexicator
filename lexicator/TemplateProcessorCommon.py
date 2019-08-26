from lexicator.TemplateUtils import test_str
from lexicator.consts import re_russian_word
from .TemplateProcessor import TemplateProcessor, TemplateProcessorBase
from .Properties import *


class TranscriptionRu(TemplateProcessor):
    def __init__(self, template: str, parser) -> None:
        super().__init__(template, parser, ['1', '2', 'lang'], True)

    def run(self, param_getter):
        lang = param_getter('lang')
        if lang and lang != 'ru':
            raise ValueError(f"Unexpected lang={lang}")
        self.parser.set_val(param_getter, '2', P_PRONUNCIATION_AUDIO, self.parser.primary_form)
        self.parser.set_val(param_getter, '1', P_IPA_TRANSCRIPTION, self.parser.primary_form)


class TranscriptionsRu(TemplateProcessor):
    def __init__(self, template: str, parser) -> None:
        super().__init__(template, parser, ['1', '2', '3', '4', 'мн2', 'lang'], True)

    def run(self, param_getter):
        lang = param_getter('lang')
        if lang and lang != 'ru':
            raise ValueError(f"Unexpected lang={lang}")
        self.parser.set_val(param_getter, '3', P_PRONUNCIATION_AUDIO, 'nom-sg')
        self.parser.set_val(param_getter, '4', P_PRONUNCIATION_AUDIO, 'nom-pl')
        self.parser.set_val(param_getter, '1', P_IPA_TRANSCRIPTION, 'nom-sg')
        self.parser.set_val(param_getter, '2', P_IPA_TRANSCRIPTION, 'nom-pl')
        self.parser.set_val(param_getter, 'мн2', P_IPA_TRANSCRIPTION, 'nom-pl2')


class Hyphenation(TemplateProcessorBase):
    # Parses {'1': 'а́', '2': '.', '3': 'ист'}, ignores '.', does some validation
    def process(self, params):
        parts = [params[str(v)] for v in sorted(params.keys(), key=lambda k: int(k))]

        new_parts = []
        merge_next = False
        for idx, part in enumerate(parts):
            if part == '.':
                if (idx != 1 and idx != len(parts) - 2) or merge_next:
                    raise ValueError('unexpected non-breaking syllable position {idx} in {parts}')
                merge_next = True
            else:
                if not re_russian_word.match(part):
                    raise ValueError('syllable {part} does not seem to be a russian word')
                if merge_next:
                    new_parts[-1] += part
                    merge_next = False
                else:
                    new_parts.append(part)

        new_value = '‧'.join(new_parts)
        P_HYPHENATION.set_claim_on_new(
            self.parser.form_by_param[self.parser.primary_form],
            ClaimValue(new_value))


class PreReformSpelling(TemplateProcessorBase):
    def process(self, params):
        form = self.parser.form_by_param[self.parser.primary_form]
        if RUSSIAN_PRE_REFORM_ID in form['representations']:
            raise ValueError(
                f"{RUSSIAN_PRE_REFORM_ID} is already set on {form}. "
                f"Old={form['representations'][RUSSIAN_PRE_REFORM_ID]['value']}, new={params}")
        form['representations'][RUSSIAN_PRE_REFORM_ID] = {
            'language': RUSSIAN_PRE_REFORM_ID,
            'value': test_str(params)
        }
