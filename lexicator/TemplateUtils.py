import re

from lexicator.Properties import mono_value, zal_normalizations


def ru_mono(v):
    return mono_value('ru', v)


re_valid_str = re.compile(r'^[^\'\<>]+$')


def test_str(v):
    if not re_valid_str.match(v):
        raise ValueError(f"Value {v} is not a valid string")
    return v


def normalize(value, normalizations):
    if value in normalizations:
        return normalizations[value]
    return value


def validate_zaliznyak1(value, param, param_getter):
    val = param_getter('зализняк')
    if not val:
        raise ValueError(f'{param}={value}, but "зализняк" param is not set')
    if normalize(val, zal_normalizations) != normalize(value, zal_normalizations):
        raise ValueError(f'зализняк={val} and {param}={value} is not yet supported')


def validate_asterisk(value, param, param_getter):
    expects = value == '1'
    z_val = param_getter('зализняк', False)
    if not z_val:
        raise ValueError(f'Param "зализняк" is not set and {param}={value}')
    if ('*' not in z_val) == expects:
        raise ValueError(
            f'Value зализняк={z_val} is {"not " if expects else ""}expected to have a "*" when {param}={value}')
