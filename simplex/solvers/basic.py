from simplex.core import AbstractSolver, Rewriter


class BasicSimplexSolver(AbstractSolver):
    def __init__(self):
        self.formatter = None
        self.rewriter = Rewriter()
        self.renames = {}
        self.summary = {
            'status': '???',
            'values': {},
            'eliminated': {},
        }
