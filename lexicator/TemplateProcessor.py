import dataclasses
from abc import ABC, abstractmethod
from typing import List, Callable, Union

from lexicator.Properties import Property, ClaimValue
from lexicator.TemplateUtils import normalize
from lexicator.consts import root_templates


class TemplateProcessorBase(ABC):
    def __init__(self, template: str, is_primary: bool = False, autorun: bool = True) -> None:
        self.template = template
        self.is_primary = is_primary
        self.autorun = autorun

    @abstractmethod
    def process(self, parser, params):
        pass


class TemplateProcessor(TemplateProcessorBase, ABC):
    def __init__(self, template: str, known_params: List[str], is_primary: bool = False, autorun: bool = True) -> None:
        super().__init__(template, is_primary, autorun)
        self.known_params = known_params
        self.expects_type = root_templates[template] if template in root_templates else None

    def process(self, parser, raw_params):
        if self.expects_type and parser.grammar_type not in self.expects_type:
            raise ValueError(f"lexeme expected to be '{self.expects_type}', but set to {parser.grammar_type}")

        if ('forms' in parser.result) == self.is_primary:
            raise ValueError(
                f"forms have {'not yet' if not self.is_primary else 'already'} been created for {self.template}")

        params = parser.resolve_lua(self.template, raw_params)
        if not params:
            return  # Skip templates with no parameters

        for p in params:
            if p not in self.known_params:
                raise ValueError(f"Unknown parameter {p}={params[p]} in {self.template}")

        done_params = set()

        def param_getter(param, mark_as_done=True):
            if mark_as_done:
                done_params.add(param)
            try:
                value = params[param]
                return None if value == '' else value
            except KeyError:
                return None

        self.run(parser, param_getter, params)

        not_done = set(params.keys()) - done_params
        if not_done:
            raise ValueError(f"Unrecognized parameters:\n" + '\n'.join((f'  * {k}={params[k]}' for k in not_done)))

    def apply_params(self, parser, param_getter, param_definitions, params: dict):
        forms = None
        for param in param_definitions:
            param_value = param_getter(param)
            if not param_value:
                continue
            definition = param_definitions[param]
            if definition is None:
                continue  # ignore this parameter

            if callable(definition):
                definition(self, parser, param_value, param, param_getter, params)
                continue

            prop, q_map, param_map = definition
            if isinstance(prop, Property):
                self.create_claim(parser, param, param_value, prop, q_map, param_map)
            elif prop == 'form':
                if forms is None:
                    forms = []
                    parser.result['forms'] = forms

                self.param_to_form(parser, param, param_getter, q_map)
            else:
                raise KeyError()

    @staticmethod
    def create_claim(parser, param, param_value, prop, q_map, param_map):
        value = normalize(param_value, param_map)
        if value is None:
            return
        if not isinstance(value, list):
            value = [value]
        for val1 in value:
            is_claim = isinstance(val1, ClaimValue)
            val = val1.value if is_claim else val1
            if val not in q_map:
                raise ValueError(f"Unknown parameter value {param}={val}"
                                 f"{f' (mapped from {param_value})' if param_value != val else ''}")
            val = q_map[val]
            if val is None:
                return
            if is_claim:
                claim_val = dataclasses.replace(val1, value=val)
            else:
                claim_val = ClaimValue(val)
            prop.set_claim_on_new(parser.result, claim_val)

    def param_to_form(self, parser, param, param_getter, features) -> None:
        parser.create_form(param, param_getter(param), features)

    @abstractmethod
    def run(self, parser, param_getter: Callable[[str, bool], Union[str, None]], params: dict):
        pass

    def get_index(self, parser):
        state = parser.get_extra_state(self.template)
        try:
            state['index'] += 1
        except KeyError:
            state['index'] = 0
        return state['index']
