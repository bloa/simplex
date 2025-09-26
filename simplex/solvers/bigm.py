from .basic import BasicSimplexSolver

from simplex.core import Tableau
from simplex.parsing import BinaryOp, Literal, Variable


class BigmSimplexSolver(BasicSimplexSolver):
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
            print(self.formatter.format_section('Big-M Method'))
            print('Updating objective function:')
            for var in self.artificial_variables:
                model.objective.root.right = BinaryOp('+', model.objective.root.right, BinaryOp('*', Literal(float('-inf')), Variable(var)))
            print(self.formatter.format_model(model))
            self.tableau = Tableau(model.objective, model.constraints, self.initial_basis)
            print('Initial basis')
            print(self.formatter.format_tableau(self.tableau))
            print()
            to_delete = []
            while True:
                coefs_obj = self.tableau.coefs_obj(self.tableau.basis)
                problematic = [var for var in self.tableau.basis if coefs_obj[var] > 0]
                if not problematic:
                    break
                to_delete += problematic
                self.do_simplex_prestep(model)
                if self.summary['status'] != '???':
                    self.do_simplex_final(model)
                    return
                print(self.formatter.format_tableau(self.tableau))
                print()
            while True:
                coefs = self.tableau.coefs_column('')
                problematic = [var for var in self.tableau.basis if coefs[var] < 0]
                if not problematic:
                    break
                self.do_simplex_prestep(model)
                if self.summary['status'] != '???':
                    self.do_simplex_final(model)
                    return
                print(self.formatter.format_tableau(self.tableau))
                print()
            for var in set(to_delete):
                if var in self.artificial_variables:
                    self.tableau.delete(var)
                else:
                    msg = 'deleting a non-artificial variable?!'
                    raise RuntimeError(msg)
            print('New simplified basis: (removing artificial variables)')
            print(self.formatter.format_tableau(self.tableau))
            print()
        else:
            self.tableau = Tableau(model.objective, model.constraints, self.initial_basis)
        print(self.formatter.format_section('Simplex Method'))
        self.do_simplex_step(model)
        while self.summary['status'] == '???':
            print(self.formatter.format_tableau(self.tableau))
            print()
            self.do_simplex_step(model)
        if self.summary['status'] == 'SOLVED':
            print()
            print('Final basis:')
            print(self.formatter.format_tableau(self.tableau))
        self.do_simplex_final(model)

    def do_simplex_prestep(self, model):
        # remove artificial variables
        coefs_obj = self.tableau.coefs_obj(self.tableau.basis)
        problematic = [var for var in self.tableau.basis if coefs_obj[var] > 0]
        if problematic:
            var_out = problematic[0]
            # sanity check
            if var_out not in self.artificial_variables:
                msg = 'positive coeficient for non-artificial basic variable?!'
                raise RuntimeError(msg)
            print(f'Removing artificial {var_out} from basis')
            candidates = self.tableau.aux_art_candidates(problematic + self.artificial_variables)
            row_out = self.tableau.row_for_basic(var_out)
            coefs = self.tableau.aux_art_coefs(row_out, candidates)
            print('    coefs:', *(f'{v}:{round(x, 8)}' for v, x in coefs.items()))
            if tmp := [v for v in candidates if coefs[v] >= 0]:
                var_in = min(tmp, key=lambda v: coefs[v])
                print(f'    -> {var_in} replaces {var_out} (min positive ratio)')
            else:
                print('... none strictly positive')
                self.summary['status'] = 'INFEASIBLE'
                return
            print('Pivoting...')
            self.tableau.pivot(var_in, var_out)
            return

        # cleanup remaining negative variables
        coefs = self.tableau.coefs_column('')
        problematic = [var for var in self.tableau.basis if coefs[var] < 0]
        if problematic:
            var_out = problematic[0]
            print(f'Removing negative {var_out} from basis')
            candidates = self.tableau.aux_art_candidates(problematic + self.artificial_variables)
            row_out = self.tableau.row_for_basic(var_out)
            coefs = self.tableau.aux_art_coefs(row_out, candidates)
            print('    coefs:', *(f'{v}:{round(x, 8)}' for v, x in coefs.items()))
            if tmp := [v for v in candidates if coefs[v] >= 0]:
                var_in = min(tmp, key=lambda v: coefs[v])
                print(f'    -> {var_in} replaces {var_out} (min positive ratio)')
            else:
                print('... none strictly positive')
                self.summary['status'] = 'INFEASIBLE'
                return
            print('Pivoting...')
            self.tableau.pivot(var_in, var_out)
            return
