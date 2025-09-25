from .basic import BasicSimplexSolver

from simplex.core import Model, Tableau
from simplex.parsing import BinaryOp, Literal, UnaryOp, Variable
from simplex.parsing import BoolTree
from simplex.utils import prefix_sort


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

        if self.summary['status'] == '???':
            print()
            print('[3.3] SOLVING')
            print('-----------------------------------')
            if self.artificial_variables:
                print()
                print('[3.3.1] Phase I : Artificial variables')
                print('------------------------------')
                print('Sub-problem:')
                out = self.formatter.format_model(self.sub_model)
                for line in out.split('\n'):
                    print(f'    {line}')
                self.tableau = Tableau(self.sub_model.objective, self.sub_model.constraints, self.initial_basis)
                for var in self.artificial_variables:
                    self.tableau.pivot(var, var)
                print('Initial basis:')
                out = self.formatter.format_tableau(self.tableau)
                for line in out.split('\n'):
                    print(f'    {line}')
                print()
                self.do_simplex_step(self.sub_model)
                while self.summary['status'] == '???':
                    out = self.formatter.format_tableau(self.tableau)
                    for line in out.split('\n'):
                        print(f'    {line}')
                    print()
                    self.do_simplex_step(self.sub_model)
                if self.tableau.data[0][''].evaluate({}) > 0:
                    self.summary['status'] = 'INFEASIBLE'
                if any(var in self.tableau.basis for var in self.artificial_variables):
                    self.summary['status'] = 'INFEASIBLE'
                if self.summary['status'] == 'SOLVED':
                    self.summary['status'] = '???'
                    tmp_basis = self.tableau.basis[:]
                    self.tableau = Tableau(model.objective, model.constraints, tmp_basis)
                    for var in tmp_basis:
                        self.tableau.pivot(var, var)
                    for var in self.artificial_variables:
                        self.tableau.delete(var)
                    print()
                    print('[3.3.2] Phase II: Initial problem')
                    print('------------------------------')
            else:
                self.tableau = Tableau(model.objective, model.constraints, self.initial_basis)
            if self.summary['status'] == '???':
                print('Initial basis:')
                out = self.formatter.format_tableau(self.tableau)
                for line in out.split('\n'):
                    print(f'    {line}')
                print()
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
                    # model.objective.root.right = BinaryOp('+', model.objective.root.right, BinaryOp('*', Literal(float('-inf')), Variable(f'{newvar}{varid}')))
                    model.objective.variables.append(f'{newvar}{varid}')
                    model.constraints.append(BoolTree(BinaryOp('>=', Variable(f'{newvar}{varid}'), Literal(0))))
                    self.artificial_variables.append(f'{newvar}{varid}')
                    # print(f'... introduced additional {newvar}{varid} >= 0 and updated objective')
                    print(f'... introduced additional {newvar}{varid} >= 0')
                self.initial_basis.append(f'{newvar}{varid}')
        model.objective.variables = prefix_sort(model.objective.variables)
        self.rewriter.normalize(model.objective)
        for c in model.constraints:
            self.rewriter.normalize(c)
        if self.artificial_variables:
            print(str(model))
            self.sub_model = Model.parse_str(str(model))
            tmp = None
            for var in self.artificial_variables:
                if tmp is None:
                    tmp = UnaryOp('-', Variable(var))
                else:
                    tmp = BinaryOp('+', tmp, UnaryOp('-', Variable(var)))
            self.sub_model.objective.root.right = tmp
            self.rewriter.normalize(self.sub_model.objective)
