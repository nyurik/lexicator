from abc import ABC, abstractmethod
from typing import List, Callable, Union

from lexicator.Properties import Property, ClaimValue, Q_FEATURES
from lexicator.ResolverViaMwParse import json_key


class TemplateProcessorBase(ABC):
    def __init__(self, template: str, parser) -> None:
        self.template = template
        self.parser = parser

    @abstractmethod
    def process(self, params):
        pass


class TemplateProcessor(TemplateProcessorBase, ABC):

    def __init__(self, template: str, parser, known_params: List[str],
                 require_forms: bool, expects_type: str = None) -> None:
        super().__init__(template, parser)
        self.known_params = known_params
        self.require_forms = require_forms
        self.expects_type = expects_type

    def process(self, params):
        if self.expects_type and self.parser.grammar_type != self.expects_type:
            raise ValueError(f"lexeme expected to be '{self.expects_type}', but set to {self.parser.grammar_type}")

        if ('forms' in self.parser.result) != self.require_forms:
            raise ValueError(
                f"forms have {'not yet' if self.require_forms else 'already'} been created for {self.template}")

        if self.template in self.parser.resolvers:
            params = self.parser.resolvers[self.template].get(json_key(self.template, params)).data

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

        self.run(param_getter)

        not_done = set(params.keys()) - done_params
        if not_done:
            raise ValueError(f"Unrecognized parameters:\n" + '\n'.join((f'* {k}={params[k]}' for k in not_done)))

    def apply_params(self, param_getter, param_definitions):
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
                val = param_map[param_value] if param_map and param_value in param_map else param_value
                if val not in q_map:
                    raise ValueError(f"Unknown parameter value {param}={val}"
                                     f"{f'(mapped from {param_value})' if param_value != val else ''}")
                prop.set_claim_on_new(self.parser.result, ClaimValue(q_map[val]))
            elif prop == 'form':
                if forms is None:
                    forms = []
                    self.parser.result['forms'] = forms

                self.param_to_form(param, param_getter, q_map)
            else:
                raise KeyError()

    def param_to_form(self, param, param_getter, features):
        param_value = param_getter(param)
        features = [Q_FEATURES[v] for v in features]
        self.parser.create_form(param, param_value, features)

    @abstractmethod
    def run(self, param_getter: Callable[[str, bool], Union[str, None]]):
        pass
