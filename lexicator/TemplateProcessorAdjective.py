import re

from .TemplateProcessor import TemplateProcessor


def validate_flag(params_to_check, enable=False):
    def validate(value, param, param_getter):
        for param in params_to_check:
            val = param_getter(param, False)
            if (val is None) == enable:
                if enable:
                    raise ValueError(f'Value {param} is expected but not given')
                else:
                    raise ValueError(f'Value {param}={val} is not expected')

    return validate


class Adjective(TemplateProcessor):
    def __init__(self, template: str, parser) -> None:
        super().__init__(template, parser, [
            'acc-pl-a', 'acc-pl-n', 'acc-sg-f', 'acc-sg-m-a', 'acc-sg-m-n', 'acc-sg-n', 'anim', 'dat-pl', 'dat-sg-f',
            'dat-sg-m', 'dat-sg-n', 'gen-pl', 'gen-sg-f', 'gen-sg-m', 'gen-sg-n', 'ins-pl', 'ins-sg-f', 'ins-sg-m',
            'ins-sg-n', 'nof', 'nol', 'nom', 'nom-pl', 'nom-sg-f', 'nom-sg-m', 'nom-sg-n', 'non', 'nowrap', 'prp-pl',
            'prp-sg-f', 'prp-sg-m', 'prp-sg-n', 'srt-pl', 'srt-sg-f', 'srt-sg-m', 'srt-sg-n', 'краткая', 'суфф'
        ], False, expects_type='adjective')

    parameters = {
        #
        # Forms
        #
        # Singular masculine
        'nom-sg-m': ('form', ('nominative', 'singular', 'masculine'), None),
        'gen-sg-m': ('form', ('genitive', 'singular', 'masculine'), None),
        'dat-sg-m': ('form', ('dative', 'singular', 'masculine'), None),
        'acc-sg-m-a': ('form', ('accusative', 'animate', 'singular', 'masculine'), None),
        'acc-sg-m-n': ('form', ('accusative', 'inanimate', 'singular', 'masculine'), None),
        'ins-sg-m': ('form', ('instrumental', 'singular', 'masculine'), None),
        'prp-sg-m': ('form', ('prepositional', 'singular', 'masculine'), None),
        'srt-sg-m': ('form', ('short-form-adjective', 'singular', 'masculine'), None),
        # Singular Neuter
        'nom-sg-n': ('form', ('nominative', 'singular', 'neuter'), None),
        'gen-sg-n': ('form', ('genitive', 'singular', 'neuter'), None),
        'dat-sg-n': ('form', ('dative', 'singular', 'neuter'), None),
        'acc-sg-n': ('form', ('accusative', 'singular', 'neuter'), None),
        'ins-sg-n': ('form', ('instrumental', 'singular', 'neuter'), None),
        'prp-sg-n': ('form', ('prepositional', 'singular', 'neuter'), None),
        'srt-sg-n': ('form', ('short-form-adjective', 'singular', 'neuter'), None),
        # Singular feminine
        'nom-sg-f': ('form', ('nominative', 'singular', 'feminine'), None),
        'gen-sg-f': ('form', ('genitive', 'singular', 'feminine'), None),
        'dat-sg-f': ('form', ('dative', 'singular', 'feminine'), None),
        'acc-sg-f': ('form', ('accusative', 'singular', 'feminine'), None),
        'ins-sg-f': ('form', ('instrumental', 'singular', 'feminine'), None),
        'prp-sg-f': ('form', ('prepositional', 'singular', 'feminine'), None),
        'srt-sg-f': ('form', ('short-form-adjective', 'singular', 'feminine'), None),
        # Plural
        'nom-pl': ('form', ('nominative', 'plural'), None),
        'gen-pl': ('form', ('genitive', 'plural'), None),
        'dat-pl': ('form', ('dative', 'plural'), None),
        'acc-pl-a': ('form', ('accusative', 'animate', 'plural'), None),
        'acc-pl-n': ('form', ('accusative', 'inanimate', 'plural'), None),
        'ins-pl': ('form', ('instrumental', 'plural'), None),
        'prp-pl': ('form', ('prepositional', 'plural'), None),
        'srt-pl': ('form', ('short-form-adjective', 'plural'), None),

        # Flags to enable/disables sections
        'краткая': validate_flag([  # If set, enables srt-*
            'srt-pl', 'srt-sg-f', 'srt-sg-m', 'srt-sg-n'], enable=True),
        'anim': validate_flag([  # Disables multiple accusative forms
            'acc-sg-m-n', 'acc-pl-n']),
        'nof': validate_flag([  # Disables feminine
            'nom-sg-f', 'gen-sg-f', 'dat-sg-f', 'acc-sg-f', 'ins-sg-f', 'prp-sg-f', 'srt-sg-f']),
        'non': validate_flag([  # Disables neuter
            'nom-sg-n', 'gen-sg-n', 'dat-sg-n', 'acc-sg-n', 'ins-sg-n', 'prp-sg-n', 'srt-sg-n']),
        'nom': validate_flag([  # Disables masculine
            'nom-sg-m', 'gen-sg-m', 'dat-sg-m', 'acc-sg-m-a', 'acc-sg-m-n', 'ins-sg-m', 'prp-sg-m', 'srt-sg-m']),
        'nol': validate_flag([  # Disables plural
            'nom-pl', 'gen-pl', 'dat-pl', 'acc-pl-a', 'acc-pl-n', 'ins-pl', 'prp-pl', 'srt-pl']),

        'nowrap': None,  # ignore CSS
        # 'суфф': '',  # if set, this text is added to all forms (probably HTML, so error out)
    }

    def run(self, param_getter):
        self.apply_params(param_getter, self.parameters)
        self.parser.primary_form = 'nom-sg-m'
