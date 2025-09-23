import pathlib
import re

from simplex.parsing import BoolTree, ObjectiveTree
from simplex.utils import prefix_sort


class Model:
    @staticmethod
    def parse_file(filename):
        with pathlib.Path.open(filename, 'r') as f:
            return Model.parse_str(f.read())

    @staticmethod
    def parse_str(s):
        model = Model()
        variables = set()
        for line in s.split('\n'):
            if re.search(r'^\s*(#|$)', line):
                continue
            if m := re.search(r'^\s*((?:min|max)[^#]+)', line):
                if model.objective is not None:
                    msg = 'Multiple objective function found'
                    raise RuntimeError(msg)
                model.objective = ObjectiveTree.from_string(m.group(1))
                continue
            if m := re.search(r'^([^#]*)(#|$)', line):
                if model.objective is None:
                    msg = 'Constraint found before objective function'
                    raise RuntimeError(msg)
                tree = BoolTree.from_string(m.group(1))
                if model.objective.root.var.name in tree.variables:
                    msg = 'Constraint uses objective as variable'
                    raise RuntimeError(msg)
                model.constraints.append(tree)
                variables.update(tree.variables)
                continue
        if model.objective is None:
            msg = 'No objective function found'
            raise RuntimeError(msg)
        model.variables = prefix_sort(variables)
        return model

    def __init__(self):
        self.objective = None
        self.constraints = []
        self.variables = []

    def __str__(self):
        out = [str(self.objective)]
        for c in self.constraints:
            out.append(str(c))
        return '\n'.join(out)
