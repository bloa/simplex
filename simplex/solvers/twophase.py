from .basic import BasicSimplexSolver

from simplex.core import Model, Tableau
from simplex.parsing import BinaryOp, UnaryOp, Variable


class TwophaseSimplexSolver(BasicSimplexSolver):
    def solve(self):
        super().solve()
        if self.summary['status'] != '???':
            return

        print()
        if self.artificial_variables:
            print(self.formatter.format_section('Phase I: Artificial Problem'))
            sub_model = Model.parse_str(str(self.model))
            obj_v = sub_model.objective.root.var()
            sub_model.variables.remove(obj_v.name)
            sub_model.objective.variables.remove(obj_v.name)
            sub_model.objective.root.left = Variable(self.names['artificial'])
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
            while self.summary['status'] == '???':
                print(self.formatter.format_tableau(self.tableau))
                print()
                self.do_simplex_step()
            if self.tableau.data[0][''].evaluate({}) > 0:
                print(self.formatter.format_decision('infeasible (phase I objective > 0)'))
                self.summary['status'] = 'INFEASIBLE'
            elif any(self.tableau.coefs_row(k)[''].evaluate({}) != 0 for k in self.artificial_variables if k in self.tableau.basis):
                print(self.formatter.format_decision('infeasible (stopped with non-zero artificial variable in basis)'))
                self.summary['status'] = 'INFEASIBLE'
            elif self.summary['status'] == 'SOLVED':
                self.summary['status'] = '???'
        if self.summary['status'] == 'SOLVED':
            tmp_tableau = self.tableau
            self.tableau = Tableau(self.model.objective, self.model.constraints, self.tableau.basis)
            self.tableau.data[1:] = tmp_tableau.data[1:]
            for k in self.tableau.basis:
                self.tableau.pivot(k, k)
        elif self.summary['status'] == '???':
            print()
            if self.artificial_variables:
                print(self.formatter.format_section('Phase II: Initial Problem'))
                print(self.formatter.format_action('Dealing with artificial variables'))
                tmp_tableau = self.tableau
                self.tableau = Tableau(self.model.objective, self.model.constraints, self.tableau.basis)
                self.tableau.data[1:] = tmp_tableau.data[1:]
                problematic = [k for k in self.artificial_variables if k in self.tableau.basis]
                if problematic:
                    tmp = ''
                    if len(problematic) > 1:
                        tmp = ', '.join(problematic[:-1]) + ', and '
                    tmp += problematic[-1]
                    print(self.formatter.format_info(f'artificial variable(s) in basis with zero-values: {tmp}'))
                    for k in problematic:
                        for k2 in self.tableau.variables:
                            if k != k2 and self.tableau.coefs_row(k)[k2].evaluate({}) != 0:
                                print(self.formatter.format_decision(f'pivoted on ({k2}, {k})'))
                                self.tableau.pivot(k2, k)
                                break
                tmp = str(self.tableau)
                for var in self.tableau.basis:
                    self.tableau.pivot(var, var)
                if str(self.tableau) != tmp:
                    print(self.formatter.format_info('fixed objective row containing basic variables'))
                for var in self.artificial_variables:
                    self.tableau.delete(var)
                print(self.formatter.format_decision('removed all artificial variables'))
            else:
                print(self.formatter.format_section('Simplex Method'))
                self.tableau = Tableau(self.model.objective, self.model.constraints, self.initial_basis)
            print('Initial basis:')
            while self.summary['status'] == '???':
                print(self.formatter.format_tableau(self.tableau))
                print()
                self.do_simplex_step()
        self.do_simplex_final()
