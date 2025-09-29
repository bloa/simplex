from .basic import BasicSimplexSolver

from simplex.core import Model, Tableau
from simplex.parsing import BinaryOp, UnaryOp, Variable


class TwophaseSimplexSolver(BasicSimplexSolver):
    def __init__(self):
        super().__init__()
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
            print(self.formatter.format_section('Phase I: Artificial Problem'))
            sub_model = Model.parse_str(str(model))
            obj_v = sub_model.objective.root.var
            while not isinstance(obj_v, Variable):
                obj_v = obj_v.right
            sub_model.variables.remove(obj_v.name)
            sub_model.objective.variables.remove(obj_v.name)
            sub_model.objective.root.var = Variable(self.names['artificial'])
            sub_model.variables.append(self.names['artificial'])
            sub_model.objective.variables.append(self.names['artificial'])
            tmp = None
            for var in self.artificial_variables:
                if tmp is None:
                    tmp = UnaryOp('-', Variable(var))
                else:
                    tmp = BinaryOp('+', tmp, UnaryOp('-', Variable(var)))
                sub_model.objective.variables.append(var)
            sub_model.objective.root.right = tmp
            self.rewriter.normalize(sub_model.objective)
            print('New problem:')
            print(self.formatter.format_model(sub_model))
            self.tableau = Tableau(sub_model.objective, sub_model.constraints, self.initial_basis)
            for var in self.artificial_variables:
                self.tableau.pivot(var, var)
            print('Initial basis:')
            print(self.formatter.format_tableau(self.tableau))
            print()
            self.do_simplex_step(sub_model)
            while self.summary['status'] == '???':
                print(self.formatter.format_tableau(self.tableau))
                print()
                self.do_simplex_step(sub_model)
            if self.tableau.data[0][''].evaluate({}) > 0:
                self.summary['status'] = 'INFEASIBLE'
            if any(var in self.tableau.basis for var in self.artificial_variables):
                self.summary['status'] = 'INFEASIBLE'
            if self.summary['status'] == 'SOLVED':
                self.summary['status'] = '???'
        if self.summary['status'] == '???':
            print()
            if self.artificial_variables:
                print(self.formatter.format_section('Phase II: Initial Problem'))
                tmp_tableau = self.tableau
                self.tableau = Tableau(model.objective, model.constraints, self.tableau.basis)
                self.tableau.data[1:] = tmp_tableau.data[1:]
                for var in self.artificial_variables:
                    self.tableau.delete(var)
                for var in self.tableau.basis:
                    self.tableau.pivot(var, var)
            else:
                print(self.formatter.format_section('Simplex Method'))
                self.tableau = Tableau(model.objective, model.constraints, self.initial_basis)
            print('Initial basis:')
            print(self.formatter.format_tableau(self.tableau))
            print()
            self.do_simplex_step(model)
            while self.summary['status'] == '???':
                print(self.formatter.format_tableau(self.tableau))
                print()
                self.do_simplex_step(model)
        self.do_simplex_final(model)
