import re
from typing import Callable, Union

from lexicator.Properties import mono_value, P_HAS_QUALITY, ClaimValue


def ru_mono(v):
    return mono_value('ru', v)


re_valid_str = re.compile(r'^[^\'\<>]+$')


def test_str(v, param):
    if not re_valid_str.match(v):
        raise ValueError(f"Value {param}='{v}' is not a valid string")
    return v


def normalize(value, normalizations):
    if callable(normalizations):
        return normalizations(value)
    if value and value in normalizations:
        return normalizations[value]
    return value


def validate_zaliznyak1(processor, parser, value, param, param_getter, params):
    val = param_getter('зализняк')
    if not val:
        raise ValueError(f'{param}={value}, but "зализняк" param is not set')
    if normalize_zal(val) != normalize_zal(value):
        raise ValueError(f'зализняк={val} and {param}={value} is not yet supported')


def validate_asterisk(processor, parser, value, param, param_getter, params):
    expects = value == '1'
    z_val = param_getter('зализняк', False)
    if not z_val:
        raise ValueError(f'Param "зализняк" is not set and {param}={value}')
    if ('*' not in z_val) == expects:
        raise ValueError(
            f'Value зализняк={z_val} is {"not " if expects else ""}expected to have a "*" when {param}={value}')


def plurale_tantum(processor, parser, value, param, param_getter, params):
    P_HAS_QUALITY.set_claim_on_new(parser.result, ClaimValue('Q138246'))


def singularia_tantum(processor, parser, value, param, param_getter, params):
    P_HAS_QUALITY.set_claim_on_new(parser.result, ClaimValue('Q604984'))


def get_bool_param(param_getter: Union[str, Callable], param, mark_as_done=True) -> bool:
    if callable(param_getter):
        value = param_getter(param, mark_as_done)
        if not value:
            return False
    else:
        value = param_getter
    if value != '1':
        raise ValueError(f'invalid boolean parameter {param}={value}')
    return True


def normalize_zal(v):
    if v == '??':
        return None
    return v.replace('(1)', '①').replace('(2)', '②').replace('(3)', '③')
