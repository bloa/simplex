from .basic import BasicSimplexSolver

from simplex.core import Tableau
from simplex.parsing import BinaryOp, Literal, Variable


class BigmSimplexSolver(BasicSimplexSolver):
    def __init__(self):
        super().__init__()
        self.m = 3628800

    def solve(self):
        super().solve()
        if self.summary['status'] != '???':
            return

        print()
        if self.artificial_variables:
            print(self.formatter.format_section('Big-M Method'))
            print('Using M =', self.m)
            print('Updating objective function:')
            for k in self.artificial_variables:
                self.model.objective.root.right = BinaryOp('+', self.model.objective.root.right, BinaryOp('*', Literal(-self.m), Variable(k)))
                self.model.objective.variables.append(k)
            print(self.formatter.format_objective(self.model))
            self.rewriter.normalize(self.model.objective)
            self.tableau = Tableau(self.model.objective, self.model.constraints, self.initial_basis)
            for var in self.artificial_variables:
                self.tableau.pivot(var, var)
            print('Initial basis')
            while self.summary['status'] == '???' and any(k in self.tableau.basis for k in self.artificial_variables):
                print(self.formatter.format_tableau(self.tableau))
                print()
                self.do_simplex_step()
            if self.summary['status'] == '???':
                print(self.formatter.format_section('Simplex Method'))
                for var in self.artificial_variables:
                    self.tableau.delete(var)
                print('Removing all artificial variables')
                print(self.formatter.format_tableau(self.tableau))
                print()
            elif any(self.tableau.coefs_row(k)[''].evaluate({}) != 0 for k in self.artificial_variables if k in self.tableau.basis):
                print(self.formatter.format_decision('infeasible (stopped with non-null artificial variable in basis)'))
                self.summary['status'] = 'INFEASIBLE'
        else:
            self.tableau = Tableau(self.model.objective, self.model.constraints, self.initial_basis)
            print(self.formatter.format_section('Simplex Method'))
            print('Initial basis')
            print(self.formatter.format_tableau(self.tableau))
            print()
        if self.summary['status'] == '???':
            self.do_simplex_step()
        while self.summary['status'] == '???':
            print(self.formatter.format_tableau(self.tableau))
            print()
            self.do_simplex_step()
        self.do_simplex_final()
