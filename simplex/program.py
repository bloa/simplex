import pathlib
import re

from .expr_nodes import BinaryOp, ExprList, Literal, UnaryOp, Variable
from .expr_tree import BoolTree, MathTree, ObjectiveTree
from .rewriter import Rewriter
from .tableau import Tableau
from .utils import prefix_unique, prefix_sort

class Program:
    @staticmethod
    def parse_file(filename):
        with pathlib.Path.open(filename, 'r') as f:
            return Program.parse_str(f.read())

    @staticmethod
    def parse_str(s):
        p = Program()
        variables = set()
        for line in s.split('\n'):
            if re.search(r'^\s*(#|$)', line):
                continue
            if m := re.search(r'^\s*((?:min|max)[^#]+)', line):
                if p.objective is not None:
                    msg = 'Multiple objective function found'
                    raise RuntimeError(msg)
                p.objective = ObjectiveTree.from_string(m.group(1))
                continue
            if m := re.search(r'^([^#]*)(#|$)', line):
                if p.objective is None:
                    msg = 'Constraint found before objective function'
                    raise RuntimeError(msg)
                tree = BoolTree.from_string(m.group(1))
                if p.objective.root.var.name in tree.variables:
                    msg = 'Constraint uses objective as variable'
                    raise RuntimeError(msg)
                p.constraints.append(tree)
                variables.update(tree.variables)
                continue
        if p.objective is None:
            msg = 'No objective function found'
            raise RuntimeError(msg)
        p.initial_variables = prefix_sort(variables)
        p.variables = p.initial_variables[:]
        return p

    def __init__(self):
        self.objective = None
        self.constraints = []
        self.variables = []
        self.initial_variables = []
        self.artificial_variables = []
        self.initial_basis = []
        self.tableau = None
        self.names = {
            'objective': 'z',
            'variable': 'x',
            'slack': 's',
            'artificial': 'a',
        }
        self.renames = {}
        self.summary = {
            'status': '???',
            'values': {},
            'eliminated': {},
        }

    def __str__(self):
        tmp = [str(self.objective)]
        neg_var = []
        pos_var = []
        for c in self.constraints:
            e = c.root
            if isinstance(e, BinaryOp) and isinstance(e.left, Variable) and isinstance(e.right, Literal) and e.right.value == 0:
                if e.op == '<=':
                    neg_var.append(e.left.name)
                elif e.op == '>=':
                    pos_var.append(e.left.name)
            else:
                tmp.append(str(e))
        if neg_var:
            tmp.append(str(BinaryOp('<=', ExprList(prefix_sort(neg_var)), Literal(0))))
        if pos_var:
            tmp.append(str(BinaryOp('>=', ExprList(prefix_sort(pos_var)), Literal(0))))
        return '\n'.join(tmp)

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

    def do_normalize(self):
        # pre-normalize
        Rewriter().normalize(self.objective)
        for c in self.constraints:
            Rewriter().normalize(c)

        # split "and" constraints and expression lists ("x1, x2 >= 0")
        tmp = []
        tmpstr = []
        for c in self.constraints:
            self._cut_and_add(c, tmp, tmpstr)
        self.constraints = tmp

        # rename objective variable
        tmp = self.objective.root.var
        while True:
            if isinstance(tmp, Variable):
                break
            tmp = tmp.right
        oldvar = tmp.name
        newvar = self.names['objective']
        if oldvar != newvar:
            if newvar in self.variables:
                msg = f'objective variable name "{newvar}" already in use as decision variable'
                raise RuntimeError(msg)
            print(f'... renaming "{oldvar}" into "{newvar}"')
            self.objective.rename(oldvar, newvar)
            self.renames[oldvar] = MathTree(Variable(newvar))

        # then rename variables
        varid = 1
        newvar = self.names['variable']
        for oldvar in self.variables[:]:
            if oldvar == self.names['objective']:
                continue
            if not re.match(rf'{newvar}\d+', oldvar):
                while f'{newvar}{varid}' in self.variables:
                    varid += 1
                print(f'... renaming "{oldvar}" into "{newvar}{varid}"')
                self.objective.rename(oldvar, f'{newvar}{varid}')
                for tree in self.constraints:
                    tree.rename(oldvar, f'{newvar}{varid}')
                self.renames[oldvar] = MathTree(Variable(f'{newvar}{varid}'))
                self.variables.remove(oldvar)
                self.variables.append(f'{newvar}{varid}')

        # re-normalize (to reorder variables)
        Rewriter().normalize(self.objective)
        for c in self.constraints:
            Rewriter().normalize(c)

        # compute variable list
        self.objective.variables = prefix_sort(self.objective.variables)
        tmp = self.objective.variables[:]
        for c in self.constraints:
            c.variables = prefix_sort(c.variables)
            tmp.extend(c.variables)
        self.variables = prefix_unique(tmp)

    def do_canonical(self):
        self.do_normalize() # just in case

        # rewrite
        Rewriter().do_canonical(self.objective)
        for c in self.constraints:
            Rewriter().do_canonical(c)

        # split new "and" constraints
        tmp = []
        tmpstr = []
        for c in self.constraints:
            self._cut_and_add(c, tmp, tmpstr)
        self.constraints = tmp

        # rename single-variable constraints
        newvar = self.names['variable']
        for oldvar in self.variables[:]:
            varid = 1
            if oldvar == self.names['objective']:
                continue
            varmin = None
            varmax = None
            in_prog = oldvar in self.objective.variables
            for c in self.constraints:
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
                self.variables.remove(oldvar)
                if oldvar in self.variables:
                    self.variables.remove(oldvar)
                if oldvar in self.initial_variables:
                    self.initial_variables.remove(oldvar)
                self.renames = {k:v for k, v in self.renames.items() if oldvar not in v.variables}
                if oldvar in self.renames:
                    del self.renames[oldvar]
                self.constraints = [c for c in self.constraints if oldvar not in c.variables]
                print('... removing associated constraints')
                continue
            # for debug: varmin <= oldvar <= varmax
            def to_expr(s):
                return MathTree.from_string(str(s)).root
            def to_norm(s):
                tree = MathTree.from_string(str(s))
                Rewriter().normalize(tree)
                return tree.root
            if varmin is None:
                if varmax is None:
                    print(f'problem: {oldvar} is free')
                    while f'{newvar}{varid}' in self.variables:
                        varid += 1
                    _varid = varid
                    varid += 1
                    while f'{newvar}{varid}' in self.variables:
                        varid += 1
                    newexpr = to_expr(f'{newvar}{_varid} - {newvar}{varid}')
                    if oldvar in self.initial_variables:
                        self.renames[oldvar] = MathTree(newexpr)
                    else:
                        for v in self.renames.values():
                            v.replace(Variable(oldvar), newexpr)
                    if oldvar in self.objective.variables:
                        self.objective.replace(Variable(oldvar), newexpr)
                    for c in self.constraints:
                        if oldvar in c.variables:
                            c.replace(Variable(oldvar), newexpr)
                    self.variables.append(f'{newvar}{_varid}')
                    self.variables.append(f'{newvar}{varid}')
                    self.constraints.append(BoolTree.from_string(f'{newvar}{_varid} >= 0'))
                    self.constraints.append(BoolTree.from_string(f'{newvar}{varid} >= 0'))
                    print(f'... introduced {newvar}{_varid} and {newvar}{varid} >= 0 such that {oldvar} = {newexpr})')
                elif varmax == 0:
                    print(f'problem: {oldvar} <= {to_norm(varmax)}')
                    while f'{newvar}{varid}' in self.variables:
                        varid += 1
                    newexpr = to_expr(f'-{newvar}{varid}')
                    newexpr2 = to_expr(f'-{oldvar}')
                    if oldvar in self.initial_variables:
                        self.renames[oldvar] = MathTree(newexpr)
                    else:
                        for v in self.renames.values():
                            v.replace(Variable(oldvar), newexpr)
                    if oldvar in self.objective.variables:
                        self.objective.replace(Variable(oldvar), newexpr)
                    for c in self.constraints:
                        if oldvar in c.variables:
                            c.replace(Variable(oldvar), newexpr)
                    self.variables.append(f'{newvar}{varid}')
                    print(f'... introduced {newvar}{varid} = {newexpr2} >= 0 (i.e., {oldvar} = {newexpr})')
                elif varmax > 0:
                    print(f'problem: {oldvar} <= {to_norm(varmax)}')
                    while f'{newvar}{varid}' in self.variables:
                        varid += 1
                    newexpr = to_expr(f'-{newvar}{varid} + {to_norm(varmax)}')
                    newexpr2 = to_expr(f'{to_norm(varmax)} - {oldvar}')
                    if oldvar in self.initial_variables:
                        self.renames[oldvar] = MathTree(newexpr)
                    else:
                        for v in self.renames.values():
                            v.replace(Variable(oldvar), newexpr)
                    if oldvar in self.objective.variables:
                        self.objective.replace(Variable(oldvar), newexpr)
                    for c in self.constraints:
                        if oldvar in c.variables:
                            c.replace(Variable(oldvar), newexpr)
                    self.variables.append(f'{newvar}{varid}')
                    print(f'... introduced {newvar}{varid} = {newexpr2} >= 0 (i.e., {oldvar} = {newexpr})')
                else:
                    print(f'problem: {oldvar} <= {to_norm(varmax)}')
                    while f'{newvar}{varid}' in self.variables:
                        varid += 1
                    newexpr = to_expr(f'-{newvar}{varid} - {to_norm(-varmax)}')
                    newexpr2 = to_expr(f'-{oldvar} - {to_norm(-varmax)}')
                    if oldvar in self.initial_variables:
                        self.renames[oldvar] = MathTree(newexpr)
                    else:
                        for v in self.renames.values():
                            v.replace(Variable(oldvar), newexpr)
                    if oldvar in self.objective.variables:
                        self.objective.replace(Variable(oldvar), newexpr)
                    for c in self.constraints:
                        if oldvar in c.variables:
                            c.replace(Variable(oldvar), newexpr)
                    self.variables.append(f'{newvar}{varid}')
                    print(f'... introduced {newvar}{varid} = {newexpr2} >= 0 (i.e., {oldvar} = {newexpr})')
            elif varmin == varmax:
                print(f'problem: {oldvar} == {to_norm(varmin)}')
                newexpr = to_norm(varmin)
                if oldvar in self.objective.variables:
                    self.objective.replace(Variable(oldvar), newexpr)
                for c in self.constraints:
                    if oldvar in c.variables:
                        c.replace(Variable(oldvar), newexpr)
                        Rewriter().normalize(c)
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
                while f'{newvar}{varid}' in self.variables:
                    varid += 1
                newexpr = to_expr(f'{newvar}{varid} + {to_norm(varmin)}')
                newexpr2 = to_expr(f'{oldvar} - {to_norm(varmin)}')
                if oldvar in self.initial_variables:
                    self.renames[oldvar] = MathTree(newexpr)
                else:
                    for v in self.renames.values():
                        v.replace(Variable(oldvar), newexpr)
                if oldvar in self.objective.variables:
                    self.objective.replace(Variable(oldvar), newexpr)
                for c in self.constraints:
                    if oldvar in c.variables:
                        c.replace(Variable(oldvar), newexpr)
                self.variables.append(f'{newvar}{varid}')
                print(f'... introduced {newvar}{varid} = {newexpr2} >= 0 (i.e., {oldvar} = {newexpr})')
            elif varmin < 0:
                if varmax:
                    print(f'problem: {to_norm(varmin)} <= {oldvar} <= {to_norm(varmax)}')
                else:
                    print(f'problem: {to_norm(varmin)} <= {oldvar}')
                while f'{newvar}{varid}' in self.variables:
                    varid += 1
                newexpr = to_expr(f'{newvar}{varid} - {to_norm(-varmin)}')
                newexpr2 = to_expr(f'{oldvar} + {to_norm(-varmin)}')
                if oldvar in self.initial_variables:
                    self.renames[oldvar] = MathTree(newexpr)
                else:
                    for v in self.renames.values():
                        v.replace(Variable(oldvar), newexpr)
                if oldvar in self.objective.variables:
                    self.objective.replace(Variable(oldvar), newexpr)
                for c in self.constraints:
                    if oldvar in c.variables:
                        c.replace(Variable(oldvar), newexpr)
                self.variables.append(f'{newvar}{varid}')
                print(f'... introduced {newvar}{varid} = {newexpr2} >= 0 (i.e., {oldvar} = {newexpr})')

        self.objective.variables = prefix_sort(self.objective.variables)
        Rewriter().do_canonical(self.objective)
        for c in self.constraints:
            Rewriter().do_canonical(c)

    def do_trivial_check(self):
        # fail on "False"
        if any(str(c) == 'False' for c in self.constraints):
            print('problem: there are trivially False constraints')
            self.summary['status'] = 'INFEASIBLE'
            return
        # remove "True"
        self.constraints = [c for c in self.constraints if str(c) != 'True']
        # fail on weird constraints
        for c in self.constraints:
            if not isinstance(c.root, BinaryOp) and c.root in ['<=', '>=']:
                msg = f'Illegal constraint: {c}'
                raise RuntimeError(msg)
        # reorder "<=" before ">="
        tmp1 = [c for c in self.constraints if c.root.op == '<=']
        if not tmp1:
            print('problem: there is no (<=) constraint')
            self.do_trivial_final()
            return
        tmp2 = [c for c in self.constraints if c.root.op == '>=']
        self.constraints = tmp1 + tmp2

    def do_standard(self):
        self.do_canonical()
        # introduce slack variables
        self.initial_basis = []
        self.artificial_variables = []
        for c in self.constraints[:]:
            newvar = self.names['slack']
            if c.root.op == '<=':
                varid = 1
                while f'{newvar}{varid}' in self.variables:
                    varid += 1
                c.root = BinaryOp('==', BinaryOp('+', c.root.left, Variable(f'{newvar}{varid}')), c.root.right)
                c.variables.append(f'{newvar}{varid}')
                Rewriter().normalize(c)
                self.variables.append(f'{newvar}{varid}')
                self.constraints.append(BoolTree(BinaryOp('>=', Variable(f'{newvar}{varid}'), Literal(0))))
                if c.root.right.evaluate({}) < 0:
                    print('problem: negative right-hand side')
                    newvar = self.names['artificial']
                    varid = 1
                    while f'{newvar}{varid}' in self.variables:
                        varid += 1
                    c.root = BinaryOp('==', BinaryOp('+', UnaryOp('-', c.root.left), Variable(f'{newvar}{varid}')), UnaryOp('-', c.root.right))
                    c.variables.append(f'{newvar}{varid}')
                    self.variables.append(f'{newvar}{varid}')
                    self.objective.root.right = BinaryOp('+', self.objective.root.right, BinaryOp('*', Literal(float('-inf')), Variable(f'{newvar}{varid}')))
                    self.objective.variables.append(f'{newvar}{varid}')
                    self.constraints.append(BoolTree(BinaryOp('>=', Variable(f'{newvar}{varid}'), Literal(0))))
                    self.artificial_variables.append(f'{newvar}{varid}')
                    print(f'... introduced additional {newvar}{varid} >= 0 and updated objective')
                self.initial_basis.append(f'{newvar}{varid}')
        self.objective.variables = prefix_sort(self.objective.variables)
        Rewriter().normalize(self.objective)
        for c in self.constraints:
            Rewriter().normalize(c)

    def do_trivial_final(self):
        tab = Tableau(self.objective, self.constraints, [])
        coefs = tab.coefs_obj_neg(self.objective.variables)
        context = {}
        inf = float('inf')
        for k, v in coefs.items():
            if v > 0:
                context[k] = inf if self.objective.root.mode == 'max' else 0
            elif v < 0:
                context[k] = inf if self.objective.root.mode == 'min' else 0
        if abs(self.objective.evaluate(context)) == inf:
            self.summary['status'] = 'UNBOUNDED'
        else:
            self.summary['status'] = 'SOLVED'

        # final values
        exprs = {v: Literal(0) for v in self.variables}
        tmp_e = MathTree(self.objective.root.var)
        Rewriter().normalize(tmp_e)
        if isinstance(tmp_e.root, Variable):
            obj_v = tmp_e.root.name
            exprs[obj_v] = Literal(self.objective.evaluate(context))
        else:
            assert isinstance(tmp_e.root.right, Variable)
            obj_v = tmp_e.root.right.name
            exprs[obj_v] = Literal(-self.objective.evaluate(context))

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
                    Rewriter().normalize(tree)
                    self.summary['values'][v] = tree.evaluate({})
                else:
                    self.summary['values'][v] = exprs[v].evaluate({})

    def do_tableau(self):
        if not self.initial_basis:
            self.do_standard()
        self.tableau = Tableau(self.objective, self.constraints, self.initial_basis)

    def do_simplex_prestep(self):
        if not self.tableau:
            self.do_tableau()

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

    def do_simplify_artificial(self, to_delete=None):
        if not self.artificial_variables:
            return

        # ensure everything is done
        if not to_delete:
            to_delete = []
        while self.summary['status'] == '???':
            coefs_obj = self.tableau.coefs_obj(self.tableau.basis)
            problematic = [var for var in self.tableau.basis if coefs_obj[var] > 0]
            if not problematic:
                break
            to_delete += problematic
            self.do_simplex_prestep()
        while self.summary['status'] == '???':
            coefs = self.tableau.coefs_column('')
            problematic = [var for var in self.tableau.basis if coefs[var] < 0]
            if not problematic:
                break
            self.do_simplex_prestep()

        # simplify
        if self.summary['status'] == '???':
            for var in set(to_delete):
                if var in self.artificial_variables:
                    self.tableau.delete(var)
                else:
                    msg = 'deleting a non-artificial variable?!'
                    raise RuntimeError(msg)

    def do_simplex_step(self):
        # look for artificial variables
        self.do_simplify_artificial()
        if self.summary['status'] != '???':
            return

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

    def do_simplex(self):
        while self.summary['status'] == '???':
            self.do_simplex_step()
        self.do_simplex_final()

    def do_simplex_final(self):
        # final values
        exprs = {v: Literal(0) for v in self.variables}
        for k, v in self.summary['eliminated'].items():
            exprs[k] = Literal(v)
        for v in self.tableau.basis:
            row = self.tableau.row_for_basic(v)
            exprs[v] = row['']
        tmp_e = MathTree(self.objective.root.var)
        Rewriter().normalize(tmp_e)
        if isinstance(tmp_e.root, Variable):
            obj_v = tmp_e.root.name
            exprs[obj_v] = self.tableau.data[0]['']
        else:
            assert isinstance(tmp_e.root.right, Variable)
            obj_v = tmp_e.root.right.name
            tmp_e = MathTree(UnaryOp('-', self.tableau.data[0]['']))
            Rewriter().normalize(tmp_e)
            exprs[obj_v] = tmp_e.root

        if self.summary['status'] == 'UNBOUNDED':
            if self.objective.root.mode == 'max':
                self.summary['values'][obj_v] = '-inf' if isinstance(self.objective.root.var, UnaryOp) else 'inf'
            elif self.objective.root.mode == 'min':
                self.summary['values'][obj_v] = 'inf' if isinstance(self.objective.root.var, UnaryOp) else '-inf'

        if self.summary['status'] == 'SOLVED':
            self.summary['values'][obj_v] = str(exprs[obj_v])
            for v in self.initial_variables:
                if v == obj_v:
                    continue
                if v in self.renames:
                    tree = MathTree(self.renames[v].root)
                    for v2 in tree.variables:
                        tree.replace(v2, exprs[v2])
                    Rewriter().normalize(tree)
                    self.summary['values'][v] = str(tree)
                else:
                    self.summary['values'][v] = str(exprs[v])
