from typing import Union, Dict, Set

import unicodedata

from lexicator.consts.consts import STRESS_SYMBOL_PRI, STRESS_SYMBOL_SEC


def title_case_re(title: str) -> str:
    if title[0].isalpha():
        return f'[{title[0].upper()}|{title[0].lower()}]{title[1:]}'
    return title


def double_title_case(dataset: Union[set, dict]) -> Union[set, dict]:
    for title in list(dataset):
        if title[0].isalpha() and title[0].islower():
            add = title[0].upper() + title[1:]
            if isinstance(dataset, set):
                dataset.add(add)
            else:
                dataset[add] = dataset[title]
    return dataset


def lower_first_letter(title: str) -> str:
    return f'{title[0].lower()}{title[1:]}'


def cleanup_root_templates(dataset: Dict[str, Union[str, set]]) -> Dict[str, Set[str]]:
    return double_title_case({
        k: None if not v else {v} if isinstance(v, str) else v for k, v in dataset.items()
    })


def remove_stress(word: str) -> str:
    return unicodedata.normalize(
        'NFC', unicodedata.normalize('NFD', word).replace(STRESS_SYMBOL_PRI, '').replace(STRESS_SYMBOL_SEC, ''))
