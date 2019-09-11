from abc import ABC, abstractmethod
from typing import List, Callable, Union

from lexicator.Properties import Property, ClaimValue, Q_FEATURES
from lexicator.consts import root_templates


class TemplateProcessorBase(ABC):
    def __init__(self, template: str, is_primary: bool = False) -> None:
        self.template = template
        self.is_primary = is_primary

    @abstractmethod
    def process(self, parser, params):
        pass


class TemplateProcessor(TemplateProcessorBase, ABC):

    def __init__(self, template: str, known_params: List[str], is_primary: bool = False) -> None:
        super().__init__(template, is_primary)
        self.known_params = known_params
        self.expects_type = root_templates[template] if template in root_templates else None

    def process(self, parser, params):
        if self.expects_type and parser.grammar_type not in self.expects_type:
            raise ValueError(f"lexeme expected to be '{self.expects_type}', but set to {parser.grammar_type}")

        if ('forms' in parser.result) == self.is_primary:
            raise ValueError(
                f"forms have {'not yet' if not self.is_primary else 'already'} been created for {self.template}")

        params = parser.resolve_lua(self.template, params)
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

        self.run(parser, param_getter)

        not_done = set(params.keys()) - done_params
        if not_done:
            raise ValueError(f"Unrecognized parameters:\n" + '\n'.join((f'  * {k}={params[k]}' for k in not_done)))

    def apply_params(self, parser, param_getter, param_definitions):
        forms = None
        for param in param_definitions:
            param_value = param_getter(param)
            if not param_value:
                continue
            definition = param_definitions[param]
            if definition is None:
                continue  # ignore this parameter

            if callable(definition):
                definition(param_value, param, param_getter)
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
        val = param_map[param_value] if param_map and param_value in param_map else param_value
        if val not in q_map:
            raise ValueError(f"Unknown parameter value {param}={val}"
                             f"{f'(mapped from {param_value})' if param_value != val else ''}")
        prop.set_claim_on_new(parser.result, ClaimValue(q_map[val]))

    def param_to_form(self, parser, param, param_getter, features) -> None:
        parser.create_form(param, param_getter(param), features)

    @abstractmethod
    def run(self, parser, param_getter: Callable[[str, bool], Union[str, None]]):
        pass

    def get_index(self, parser):
        state = parser.get_extra_state(self.template)
        try:
            state['index'] += 1
        except KeyError:
            state['index'] = 0
        return state['index']