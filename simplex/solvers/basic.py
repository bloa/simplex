import re

from simplex.core import AbstractSolver, Rewriter, Tableau
from simplex.parsing import BinaryOp, ExprList, Literal, UnaryOp, Variable
from simplex.parsing import BoolTree, MathTree
from simplex.utils import prefix_sort, prefix_unique


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

    def solve(self, model):
        self.initial_variables = model.variables[:]
        self.artificial_variables = []
        self.initial_basis = []
        tmp = self.formatter.format_model(model)

        if self.summary['status'] == '???':
            print()
            print('[3.1] CONVERTING TO CANONICAL FORM')
            print('-----------------------------------')
            self.do_canonical(model)
            out = self.formatter.format_model(model)
            if out == tmp:
                print('Program already in canonical form')
            else:
                print('Program in canonical form:')
                for line in out.split('\n'):
                    print(f'    {line}')
                tmp = out
            self.do_trivial_check(model)
            out = self.formatter.format_model(model)
            if self.summary['status'] == '???' and out != tmp:
                print('Program in canonical form: (reordered)')
                for line in out.split('\n'):
                    print(f'    {line}')
                tmp = out

        if self.summary['status'] == '???':
            print()
            print('[3.2] CONVERTING TO STANDARD FORM')
            print('-----------------------------------')
            self.do_standard(model)
            out = self.formatter.format_model(model)
            if out == tmp:
                print('Program already in standard form')
            else:
                print('Program in standard form:')
                for line in out.split('\n'):
                    print(f'    {line}')

    def _cut_and_add(self, expr, acc, accstr):
        if isinstance(expr.root, ExprList):
            for e in expr.root.exprlist:
                self._cut_and_add(BoolTree(e), acc, accstr)
            return
        if isinstance(expr.root, BinaryOp):
            if expr.root.op == 'and':
                self._cut_and_add(BoolTree(expr.root.left), acc, accstr)
                self._cut_and_add(BoolTree(expr.root.right), acc, accstr)
                return
            if expr.root.op == 'or':
                msg = '"or" expressions may not be linearisable'
                raise RuntimeError(msg)
        exprstr = str(expr)
        if not any(exprstr == s for s in accstr):
            acc.append(expr)
            accstr.append(exprstr)

    def do_normalize(self, model):
        # pre-normalize
        self.rewriter.normalize(model.objective)
        for c in model.constraints:
            self.rewriter.normalize(c)

        # split "and" constraints and expression lists ("x1, x2 >= 0")
        tmp = []
        tmpstr = []
        for c in model.constraints:
            self._cut_and_add(c, tmp, tmpstr)
        model.constraints = tmp

        # rename objective variable
        tmp = model.objective.root.var
        while True:
            if isinstance(tmp, Variable):
                break
            tmp = tmp.right
        oldvar = tmp.name
        newvar = self.names['objective']
        if oldvar != newvar:
            if newvar in model.variables:
                msg = f'objective variable name "{newvar}" already in use as decision variable'
                raise RuntimeError(msg)
            print(f'... renaming "{oldvar}" into "{newvar}"')
            model.objective.rename(oldvar, newvar)
            self.renames[oldvar] = MathTree(Variable(newvar))

        # then rename variables
        varid = 1
        newvar = self.names['variable']
        for oldvar in model.variables[:]:
            if oldvar == self.names['objective']:
                continue
            if not re.match(rf'{newvar}\d+', oldvar):
                while f'{newvar}{varid}' in model.variables:
                    varid += 1
                print(f'... renaming "{oldvar}" into "{newvar}{varid}"')
                model.objective.rename(oldvar, f'{newvar}{varid}')
                for tree in model.constraints:
                    tree.rename(oldvar, f'{newvar}{varid}')
                self.renames[oldvar] = MathTree(Variable(f'{newvar}{varid}'))
                model.variables.remove(oldvar)
                model.variables.append(f'{newvar}{varid}')

        # re-normalize (to reorder variables)
        self.rewriter.normalize(model.objective)
        for c in model.constraints:
            self.rewriter.normalize(c)

        # compute variable list
        model.objective.variables = prefix_sort(model.objective.variables)
        tmp = model.objective.variables[:]
        for c in model.constraints:
            c.variables = prefix_sort(c.variables)
            tmp.extend(c.variables)
        model.variables = prefix_unique(tmp)

    def do_canonical(self, model):
        self.do_normalize(model) # just in case

        # rewrite
        self.rewriter.do_canonical(model.objective)
        for c in model.constraints:
            self.rewriter.do_canonical(c)

        # split new "and" constraints
        tmp = []
        tmpstr = []
        for c in model.constraints:
            self._cut_and_add(c, tmp, tmpstr)
        model.constraints = tmp

        # rename single-variable constraints
        newvar = self.names['variable']
        for oldvar in model.variables[:]:
            varid = 1
            if oldvar == self.names['objective']:
                continue
            varmin = None
            varmax = None
            in_prog = oldvar in model.objective.variables
            for c in model.constraints:
                if oldvar not in c.variables:
                    continue
                if c.variables != [oldvar]:
                    in_prog = True
                    continue
                vleft = c.root.left.left.evaluate({}) if isinstance(c.root.left, BinaryOp) else 1
                vright = c.root.right.evaluate({})
                if (c.root.op == '>=' and vleft > 0) or (c.root.op == '<=' and vleft < 0):
                    varmin = max(varmin, vright/vleft) if varmin else vright/vleft
                else:
                    varmax = min(varmax, vright/vleft) if varmax else vright/vleft
            if not in_prog:
                print(f'problem: {oldvar} is unused')
                model.variables.remove(oldvar)
                if oldvar in model.variables:
                    model.variables.remove(oldvar)
                if oldvar in self.initial_variables:
                    self.initial_variables.remove(oldvar)
                self.renames = {k:v for k, v in self.renames.items() if oldvar not in v.variables}
                if oldvar in self.renames:
                    del self.renames[oldvar]
                model.constraints = [c for c in model.constraints if oldvar not in c.variables]
                print('... removing associated constraints')
                continue
            # for debug: varmin <= oldvar <= varmax
            def to_expr(s):
                return MathTree.from_string(str(s)).root
            def to_norm(s):
                tree = MathTree.from_string(str(s))
                self.rewriter.normalize(tree)
                return tree.root
            if varmin is None:
                if varmax is None:
                    print(f'problem: {oldvar} is free')
                    while f'{newvar}{varid}' in model.variables:
                        varid += 1
                    _varid = varid
                    varid += 1
                    while f'{newvar}{varid}' in model.variables:
                        varid += 1
                    newexpr = to_expr(f'{newvar}{_varid} - {newvar}{varid}')
                    if oldvar in self.initial_variables:
                        self.renames[oldvar] = MathTree(newexpr)
                    else:
                        for v in self.renames.values():
                            v.replace(Variable(oldvar), newexpr)
                    if oldvar in model.objective.variables:
                        model.objective.replace(Variable(oldvar), newexpr)
                    for c in model.constraints:
                        if oldvar in c.variables:
                            c.replace(Variable(oldvar), newexpr)
                    model.variables.append(f'{newvar}{_varid}')
                    model.variables.append(f'{newvar}{varid}')
                    model.constraints.append(BoolTree.from_string(f'{newvar}{_varid} >= 0'))
                    model.constraints.append(BoolTree.from_string(f'{newvar}{varid} >= 0'))
                    print(f'... introduced {newvar}{_varid} and {newvar}{varid} >= 0 such that {oldvar} = {newexpr})')
                elif varmax == 0:
                    print(f'problem: {oldvar} <= {to_norm(varmax)}')
                    while f'{newvar}{varid}' in model.variables:
                        varid += 1
                    newexpr = to_expr(f'-{newvar}{varid}')
                    newexpr2 = to_expr(f'-{oldvar}')
                    if oldvar in self.initial_variables:
                        self.renames[oldvar] = MathTree(newexpr)
                    else:
                        for v in self.renames.values():
                            v.replace(Variable(oldvar), newexpr)
                    if oldvar in model.objective.variables:
                        model.objective.replace(Variable(oldvar), newexpr)
                    for c in model.constraints:
                        if oldvar in c.variables:
                            c.replace(Variable(oldvar), newexpr)
                    model.variables.append(f'{newvar}{varid}')
                    print(f'... introduced {newvar}{varid} = {newexpr2} >= 0 (i.e., {oldvar} = {newexpr})')
                elif varmax > 0:
                    print(f'problem: {oldvar} <= {to_norm(varmax)}')
                    while f'{newvar}{varid}' in model.variables:
                        varid += 1
                    newexpr = to_expr(f'-{newvar}{varid} + {to_norm(varmax)}')
                    newexpr2 = to_expr(f'{to_norm(varmax)} - {oldvar}')
                    if oldvar in self.initial_variables:
                        self.renames[oldvar] = MathTree(newexpr)
                    else:
                        for v in self.renames.values():
                            v.replace(Variable(oldvar), newexpr)
                    if oldvar in model.objective.variables:
                        model.objective.replace(Variable(oldvar), newexpr)
                    for c in model.constraints:
                        if oldvar in c.variables:
                            c.replace(Variable(oldvar), newexpr)
                    model.variables.append(f'{newvar}{varid}')
                    print(f'... introduced {newvar}{varid} = {newexpr2} >= 0 (i.e., {oldvar} = {newexpr})')
                else:
                    print(f'problem: {oldvar} <= {to_norm(varmax)}')
                    while f'{newvar}{varid}' in model.variables:
                        varid += 1
                    newexpr = to_expr(f'-{newvar}{varid} - {to_norm(-varmax)}')
                    newexpr2 = to_expr(f'-{oldvar} - {to_norm(-varmax)}')
                    if oldvar in self.initial_variables:
                        self.renames[oldvar] = MathTree(newexpr)
                    else:
                        for v in self.renames.values():
                            v.replace(Variable(oldvar), newexpr)
                    if oldvar in model.objective.variables:
                        model.objective.replace(Variable(oldvar), newexpr)
                    for c in model.constraints:
                        if oldvar in c.variables:
                            c.replace(Variable(oldvar), newexpr)
                    model.variables.append(f'{newvar}{varid}')
                    print(f'... introduced {newvar}{varid} = {newexpr2} >= 0 (i.e., {oldvar} = {newexpr})')
            elif varmin == varmax:
                print(f'problem: {oldvar} == {to_norm(varmin)}')
                newexpr = to_norm(varmin)
                if oldvar in model.objective.variables:
                    model.objective.replace(Variable(oldvar), newexpr)
                for c in model.constraints:
                    if oldvar in c.variables:
                        c.replace(Variable(oldvar), newexpr)
                        self.rewriter.normalize(c)
                self.summary['eliminated'][oldvar] = to_norm(varmin)
                print(f'... eliminated {oldvar} everywhere')
            elif varmax and varmin > varmax:
                print(f'problem: {oldvar} <= {to_norm(varmax)} and {oldvar} >= {to_norm(varmin)}')
                self.summary['status'] = 'INFEASIBLE'
                return
            elif varmin > 0:
                if varmax:
                    print(f'problem: {to_norm(varmin)} <= {oldvar} <= {to_norm(varmax)}')
                else:
                    print(f'problem: {to_norm(varmin)} <= {oldvar}')
                while f'{newvar}{varid}' in model.variables:
                    varid += 1
                newexpr = to_expr(f'{newvar}{varid} + {to_norm(varmin)}')
                newexpr2 = to_expr(f'{oldvar} - {to_norm(varmin)}')
                if oldvar in self.initial_variables:
                    self.renames[oldvar] = MathTree(newexpr)
                else:
                    for v in self.renames.values():
                        v.replace(Variable(oldvar), newexpr)
                if oldvar in model.objective.variables:
                    model.objective.replace(Variable(oldvar), newexpr)
                for c in model.constraints:
                    if oldvar in c.variables:
                        c.replace(Variable(oldvar), newexpr)
                model.variables.append(f'{newvar}{varid}')
                print(f'... introduced {newvar}{varid} = {newexpr2} >= 0 (i.e., {oldvar} = {newexpr})')
            elif varmin < 0:
                if varmax:
                    print(f'problem: {to_norm(varmin)} <= {oldvar} <= {to_norm(varmax)}')
                else:
                    print(f'problem: {to_norm(varmin)} <= {oldvar}')
                while f'{newvar}{varid}' in model.variables:
                    varid += 1
                newexpr = to_expr(f'{newvar}{varid} - {to_norm(-varmin)}')
                newexpr2 = to_expr(f'{oldvar} + {to_norm(-varmin)}')
                if oldvar in self.initial_variables:
                    self.renames[oldvar] = MathTree(newexpr)
                else:
                    for v in self.renames.values():
                        v.replace(Variable(oldvar), newexpr)
                if oldvar in model.objective.variables:
                    model.objective.replace(Variable(oldvar), newexpr)
                for c in model.constraints:
                    if oldvar in c.variables:
                        c.replace(Variable(oldvar), newexpr)
                model.variables.append(f'{newvar}{varid}')
                print(f'... introduced {newvar}{varid} = {newexpr2} >= 0 (i.e., {oldvar} = {newexpr})')

        model.objective.variables = prefix_sort(model.objective.variables)
        self.rewriter.do_canonical(model.objective)
        for c in model.constraints:
            self.rewriter.do_canonical(c)

    def do_trivial_check(self, model):
        # fail on "False"
        if any(str(c) == 'False' for c in model.constraints):
            print('problem: there are trivially False constraints')
            self.summary['status'] = 'INFEASIBLE'
            return
        # remove "True"
        model.constraints = [c for c in model.constraints if str(c) != 'True']
        # fail on weird constraints
        for c in model.constraints:
            if not isinstance(c.root, BinaryOp) and c.root in ['<=', '>=']:
                msg = f'Illegal constraint: {c}'
                raise RuntimeError(msg)
        # reorder "<=" before ">="
        tmp1 = [c for c in model.constraints if c.root.op == '<=']
        if not tmp1:
            print('problem: there is no (<=) constraint')
            self.do_trivial_final(model)
            return
        tmp2 = [c for c in model.constraints if c.root.op == '>=']
        model.constraints = tmp1 + tmp2

    def do_trivial_final(self, model):
        tab = Tableau(model.objective, model.constraints, [])
        coefs = tab.coefs_obj_neg(model.objective.variables)
        context = {}
        inf = float('inf')
        for k, v in coefs.items():
            if v > 0:
                context[k] = inf if model.objective.root.mode == 'max' else 0
            elif v < 0:
                context[k] = inf if model.objective.root.mode == 'min' else 0
        if abs(model.objective.evaluate(context)) == inf:
            self.summary['status'] = 'UNBOUNDED'
        else:
            self.summary['status'] = 'SOLVED'

        # final values
        exprs = {v: Literal(0) for v in model.variables}
        tmp_e = MathTree(model.objective.root.var)
        self.rewriter.normalize(tmp_e)
        if isinstance(tmp_e.root, Variable):
            obj_v = tmp_e.root.name
            exprs[obj_v] = Literal(model.objective.evaluate(context))
        else:
            assert isinstance(tmp_e.root.right, Variable)
            obj_v = tmp_e.root.right.name
            exprs[obj_v] = Literal(-model.objective.evaluate(context))

        self.summary['values'] = {}
        self.summary['values'][obj_v] = exprs[obj_v].evaluate({})

        if self.summary['status'] == 'SOLVED':
            for v in self.initial_variables:
                if v == obj_v:
                    continue
                if v in self.renames:
                    tree = MathTree(self.renames[v].root)
                    for v2 in tree.variables:
                        tree.replace(v2, exprs[v2])
                    self.rewriter.normalize(tree)
                    self.summary['values'][v] = tree.evaluate({})
                else:
                    self.summary['values'][v] = exprs[v].evaluate({})

    def do_simplex_step(self, model):
        # sanity check
        for line in self.tableau.data[1:]:
            if line[''].evaluate({}) < 0:
                msg = 'negative RHS for basic variable?!'
                raise RuntimeError(msg)

        print('Searching for a variable to enter the basis')
        candidates = [v for v in self.tableau.variables if v not in self.tableau.basis]
        coefs = self.tableau.coefs_obj_neg(candidates)
        candidates = [v for v in candidates if coefs[v] > 0]
        if not candidates:
            print('   ... none strictly positive')
            self.summary['status'] = 'SOLVED'
            return
        print('    coefs:', *(f'{v}:{round(x, 8)}' for v, x in coefs.items()))
        var_in = max(candidates, key=lambda v: coefs[v])
        print(f'    -> {var_in} (max positive coef)')

        print('Searching for a variable to exit the basis')
        col_lit = self.tableau.coefs_column('')
        col_var = self.tableau.coefs_column(var_in)
        candidates = [v for v in self.tableau.basis if col_var[v] > 0]
        coefs = {v: col_lit[v]/col_var[v] for v in candidates}
        if tmp := [v for v in candidates if coefs[v] >= 0]:
            var_out = min(tmp, key=lambda v: coefs[v])
            print('    ratios:', *(f'{v}:{round(x, 8)}' for v, x in coefs.items()))
            print(f'    -> {var_out} (min positive ratio)')
        else:
            print('    ... no strictly positive coef')
            self.summary['status'] = 'UNBOUNDED'
            return

        print('Pivoting...')
        self.tableau.pivot(var_in, var_out)

    def do_simplex_final(self, model):
        # final values
        exprs = {v: Literal(0) for v in model.variables}
        for k, v in self.summary['eliminated'].items():
            exprs[k] = Literal(v)
        for v in self.tableau.basis:
            row = self.tableau.row_for_basic(v)
            exprs[v] = row['']
        tmp_e = MathTree(model.objective.root.var)
        self.rewriter.normalize(tmp_e)
        if isinstance(tmp_e.root, Variable):
            obj_v = tmp_e.root.name
            exprs[obj_v] = self.tableau.data[0]['']
        else:
            assert isinstance(tmp_e.root.right, Variable)
            obj_v = tmp_e.root.right.name
            tmp_e = MathTree(UnaryOp('-', self.tableau.data[0]['']))
            self.rewriter.normalize(tmp_e)
            exprs[obj_v] = tmp_e.root

        if self.summary['status'] == 'UNBOUNDED':
            if model.objective.root.mode == 'max':
                self.summary['values'][obj_v] = '-inf' if isinstance(model.objective.root.var, UnaryOp) else 'inf'
            elif model.objective.root.mode == 'min':
                self.summary['values'][obj_v] = 'inf' if isinstance(model.objective.root.var, UnaryOp) else '-inf'

        if self.summary['status'] == 'SOLVED':
            self.summary['values'][obj_v] = str(exprs[obj_v])
            for v in self.initial_variables:
                if v == obj_v:
                    continue
                if v in self.renames:
                    tree = MathTree(self.renames[v].root)
                    for v2 in tree.variables:
                        tree.replace(v2, exprs[v2])
                    self.rewriter.normalize(tree)
                    self.summary['values'][v] = str(tree)
                else:
                    self.summary['values'][v] = str(exprs[v])
