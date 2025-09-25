from .basic import BasicSimplexSolver

from simplex.core import Tableau
from simplex.parsing import BinaryOp, Literal, UnaryOp, Variable
from simplex.parsing import BoolTree
from simplex.utils import prefix_sort


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

        if self.summary['status'] == '???':
            print()
            print('[3.3] SOLVING')
            print('-----------------------------------')
            self.tableau = Tableau(model.objective, model.constraints, self.initial_basis)
        if self.summary['status'] == '???':
            print('Initial basis:')
            out = self.formatter.format_tableau(self.tableau)
            for line in out.split('\n'):
                print(f'    {line}')
            print()

        if self.summary['status'] == '???':
            if self.artificial_variables:
                print('[3.3.1] Big-M method')
                print('------------------------------')
                to_delete = []
                while self.summary['status'] == '???':
                    coefs_obj = self.tableau.coefs_obj(self.tableau.basis)
                    problematic = [var for var in self.tableau.basis if coefs_obj[var] > 0]
                    if not problematic:
                        break
                    to_delete += problematic
                    self.do_simplex_prestep(model)
                    if self.summary['status'] == '???':
                        out = self.formatter.format_tableau(self.tableau)
                        for line in out.split('\n'):
                            print(f'    {line}')
                        print()
                while self.summary['status'] == '???':
                    coefs = self.tableau.coefs_column('')
                    problematic = [var for var in self.tableau.basis if coefs[var] < 0]
                    if not problematic:
                        break
                    self.do_simplex_prestep(model)
                    if self.summary['status'] == '???':
                        out = self.formatter.format_tableau(self.tableau)
                        for line in out.split('\n'):
                            print(f'    {line}')
                        print()
                if self.summary['status'] == '???':
                    for var in set(to_delete):
                        if var in self.artificial_variables:
                            self.tableau.delete(var)
                        else:
                            msg = 'deleting a non-artificial variable?!'
                            raise RuntimeError(msg)
                    print('New simplified basis: (removing artificial variables)')
                    out = self.formatter.format_tableau(self.tableau)
                    for line in out.split('\n'):
                        print(f'    {line}')
                    print()
                    print('[3.3.2] Simplex method')
                    print('------------------------------')
            if self.summary['status'] == '???':
                self.do_simplex_step(model)
                while self.summary['status'] == '???':
                    out = self.formatter.format_tableau(self.tableau)
                    for line in out.split('\n'):
                        print(f'    {line}')
                    print()
                    self.do_simplex_step(model)
            if self.summary['status'] == '???':
                print()
                print('Final basis:')
                out = self.formatter.format_tableau(self.tableau)
                for line in out.split('\n'):
                    print(f'    {line}')
            self.do_simplex_final(model)

    def do_standard(self, model):
        self.do_canonical(model)
        # introduce slack variables
        self.initial_basis = []
        self.artificial_variables = []
        for c in model.constraints[:]:
            newvar = self.names['slack']
            if c.root.op == '<=':
                varid = 1
                while f'{newvar}{varid}' in model.variables:
                    varid += 1
                c.root = BinaryOp('==', BinaryOp('+', c.root.left, Variable(f'{newvar}{varid}')), c.root.right)
                c.variables.append(f'{newvar}{varid}')
                self.rewriter.normalize(c)
                model.variables.append(f'{newvar}{varid}')
                model.constraints.append(BoolTree(BinaryOp('>=', Variable(f'{newvar}{varid}'), Literal(0))))
                if c.root.right.evaluate({}) < 0:
                    print('problem: negative right-hand side')
                    newvar = self.names['artificial']
                    varid = 1
                    while f'{newvar}{varid}' in model.variables:
                        varid += 1
                    c.root = BinaryOp('==', BinaryOp('+', UnaryOp('-', c.root.left), Variable(f'{newvar}{varid}')), UnaryOp('-', c.root.right))
                    c.variables.append(f'{newvar}{varid}')
                    model.variables.append(f'{newvar}{varid}')
                    model.objective.root.right = BinaryOp('+', model.objective.root.right, BinaryOp('*', Literal(float('-inf')), Variable(f'{newvar}{varid}')))
                    model.objective.variables.append(f'{newvar}{varid}')
                    model.constraints.append(BoolTree(BinaryOp('>=', Variable(f'{newvar}{varid}'), Literal(0))))
                    self.artificial_variables.append(f'{newvar}{varid}')
                    print(f'... introduced additional {newvar}{varid} >= 0 and updated objective')
                self.initial_basis.append(f'{newvar}{varid}')
        model.objective.variables = prefix_sort(model.objective.variables)
        self.rewriter.normalize(model.objective)
        for c in model.constraints:
            self.rewriter.normalize(c)

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
