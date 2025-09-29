from .basic import BasicSimplexSolver

from simplex.core import Tableau
from simplex.parsing import BinaryOp, Literal, Variable


class BigmSimplexSolver(BasicSimplexSolver):
    def __init__(self):
        super().__init__()
        self.m = 3628800
        self.names = {
            'objective': 'z',
            'variable': 'x',
            'slack': 's',
            'artificial': 'a',
        }

    def solve(self, model):
        super().solve(model)
        if self.summary['status'] != '???':
            return

        print()
        if self.artificial_variables:
            print(self.formatter.format_section('Big-M Method'))
            print('Using M =', self.m)
            print('Updating objective function:')
            for var in self.artificial_variables:
                model.objective.root.right = BinaryOp('+', model.objective.root.right, BinaryOp('*', Literal(-self.m), Variable(var)))
            print(self.formatter.format_objective(model))
            self.tableau = Tableau(model.objective, model.constraints, self.initial_basis)
            for var in self.artificial_variables:
                self.tableau.pivot(var, var)
            print('Initial basis')
            print(self.formatter.format_tableau(self.tableau))
            print()
            while any(k in self.tableau.basis for k in self.artificial_variables):
                self.do_simplex_step(model)
                if self.summary['status'] != '???':
                    self.summary['status'] = 'INFEASIBLE'
                    return
                print(self.formatter.format_tableau(self.tableau))
                print()

            print(self.formatter.format_section('Simplex Method'))
            for var in self.artificial_variables:
                self.tableau.delete(var)
            print('Removing all artificial variables')
            print(self.formatter.format_tableau(self.tableau))
            print()
        else:
            self.tableau = Tableau(model.objective, model.constraints, self.initial_basis)
            print(self.formatter.format_section('Simplex Method'))
            print('Initial basis')
            print(self.formatter.format_tableau(self.tableau))
            print()
        self.do_simplex_step(model)
        while self.summary['status'] == '???':
            print(self.formatter.format_tableau(self.tableau))
            print()
            self.do_simplex_step(model)
        self.do_simplex_final(model)
