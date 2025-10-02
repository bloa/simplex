import re

from simplex.core import AbstractSolver, Model, Rewriter, Tableau
from simplex.parsing import BinaryOp, ExprList, Literal, UnaryOp, Variable
from simplex.parsing import BoolTree, MathTree, ObjectiveTree
from simplex.utils import prefix_sort, prefix_unique


class BasicSimplexSolver(AbstractSolver):
    def __init__(self):
        self.convert_from_dual = False
        self.convert_to_dual = False
        self.formatter = None
        self.rewriter = Rewriter()
        self.renames = {}
        self.summary = {
            'status': '???',
            'values': {},
            'eliminated': {},
        }
        self.names = {
            'objective': 'z',
            'dual_objective': 'w',
            'variable': 'x',
            'dual_variable': 'y',
            'slack': 's',
            'artificial': 'a',
        }

    def solve(self):
        self.initial_variables = self.model.variables[:]
        self.artificial_variables = []
        self.initial_basis = []

        print(self.formatter.format_section('Preparation'))

        print(self.formatter.format_step('Normalization'))
        print(self.formatter.format_action('Rewriting program'))
        tmp = str(self.model)
        self.do_normalize(rename=True)
        out = self.formatter.format_model(self.model)
        if out == tmp:
            print(self.formatter.format_decision('skipped: program already normalized'))
        else:
            print(out)
            tmp = out

        if self.convert_from_dual != self.convert_to_dual:
            print()
            if self.convert_from_dual:
                print(self.formatter.format_step('Primal form'))
            else:
                print(self.formatter.format_step('Dual form'))
            print(self.formatter.format_action('Rewriting program'))
            self.do_dual()
            out = self.formatter.format_model(self.model)
            print(out)
            tmp = out
            self.do_trivial_logic_check()
            if self.summary['status'] != '???':
                return

        print()
        print(self.formatter.format_step('Canonical form'))
        print(self.formatter.format_action('Rewriting program'))
        self.do_canonical()
        out = self.formatter.format_model(self.model)
        if out == tmp:
            print(self.formatter.format_decision('skipped: program already in canonical form'))
        else:
            print(out)
            tmp = out
        self.do_trivial_check()
        if self.summary['status'] != '???':
            return

        print()
        print(self.formatter.format_step('Standard form'))
        print(self.formatter.format_action('Rewriting program'))
        self.do_standard()
        out = self.formatter.format_model(self.model)
        if out == tmp:
            print(self.formatter.format_decision('skipped: program already in standard form'))
        else:
            print(out)
        if self.summary['status'] != '???':
            return

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

    def do_normalize(self, rename=True):
        # pre-normalize
        self.rewriter.normalize(self.model.objective)
        for c in self.model.constraints:
            self.rewriter.normalize(c)

        # split "and" constraints and expression lists ("x1, x2 >= 0")
        tmp = []
        tmpstr = []
        for c in self.model.constraints:
            self._cut_and_add(c, tmp, tmpstr)
        self.model.constraints = tmp

        if rename:
            # rename objective variable
            oldvar = self.model.objective.root.var().name
            newvar = self.names['dual_objective' if self.convert_from_dual else 'objective']
            if oldvar != newvar:
                if newvar in self.model.variables:
                    msg = f'objective variable name "{newvar}" already in use as decision variable'
                    raise RuntimeError(msg)
                print(self.formatter.format_decision(f'renamed "{oldvar}" into "{newvar}"'))
                self.model.objective.rename(oldvar, newvar)
                self.renames[oldvar] = MathTree(Variable(newvar))
                self.model.variables = [newvar if var == oldvar else var for var in self.model.variables]

            # then rename variables
            varid = 1
            newvar = self.names['dual_variable' if self.convert_from_dual else 'variable']
            for oldvar in self.model.variables[:]:
                if oldvar == self.names['dual_objective' if self.convert_from_dual else 'objective']:
                    continue
                if not re.match(rf'{newvar}\d+', oldvar):
                    while f'{newvar}{varid}' in self.model.variables:
                        varid += 1
                    print(self.formatter.format_decision(f'renamed "{oldvar}" into "{newvar}{varid}"'))
                    self.model.objective.rename(oldvar, f'{newvar}{varid}')
                    for tree in self.model.constraints:
                        tree.rename(oldvar, f'{newvar}{varid}')
                    self.renames[oldvar] = MathTree(Variable(f'{newvar}{varid}'))
                    self.model.variables.remove(oldvar)
                    self.model.variables.append(f'{newvar}{varid}')

        # re-normalize (to reorder variables)
        self.rewriter.normalize(self.model.objective)
        for c in self.model.constraints:
            self.rewriter.normalize(c)

        # compute variable list
        self.model.objective.variables = prefix_sort(self.model.objective.variables)
        tmp = self.model.objective.variables[:]
        for c in self.model.constraints:
            c.variables = prefix_sort(c.variables)
            tmp.extend(c.variables)
        self.model.variables = prefix_unique(tmp)

    def do_dual(self):
        dual_model = Model()

        true_constraints = []
        pos_vars = []
        neg_vars = []
        for c in self.model.constraints:
            if isinstance(c.root.left, Variable) and isinstance(c.root.right, Literal) and c.root.right.value == 0:
                if c.root.op == '>=':
                    pos_vars.append(c.root.left.name)
                elif c.root.op == '<=':
                    neg_vars.append(c.root.left.name)
            else:
                true_constraints.append(c)

        primal_coefs = []
        primal_coefs.append(Tableau.aux_data(self.model.objective.root, self.model.variables))
        for c in true_constraints:
            primal_coefs.append(Tableau.aux_data(c.root, self.model.variables))
        primal_variables = list(primal_coefs[0].keys())[1:-1]

        # variables
        newvar = self.names['variable' if self.convert_from_dual else 'dual_variable']
        varid = 1
        variables = []
        for c in true_constraints:
            while f'{newvar}{varid}' in self.model.variables or f'{newvar}{varid}' in self.initial_variables:
                varid += 1
            variables.append(f'{newvar}{varid}')
            if self.model.objective.root.mode == 'max':
                op = '<=' if c.root.op == '>=' else '>='
            else:
                op = c.root.op
            if c.root.op != '==':
                dual_model.constraints.append(BoolTree.from_string(f'{newvar}{varid} {op} 0'))
            varid += 1
        if variables:
            tmp = ', '.join(variables[:-1])
            if len(variables) > 1:
                tmp += ', and '
                print(self.formatter.format_decision(f'used {tmp}{variables[-1]} as new variable(s)'))

        # constraints
        for k in primal_variables:
            op = '=='
            if k in pos_vars:
                op = '>=' if self.model.objective.root.mode == 'max' else '<='
            elif k in neg_vars:
                op = '<=' if self.model.objective.root.mode == 'max' else '>='
            tmp = Literal(0)
            for i,k2 in enumerate(variables):
                tmp = BinaryOp('+', tmp, BinaryOp('*', primal_coefs[i+1][k], k2))
            rhs = primal_coefs[0][k]
            dual_model.constraints.append(BoolTree.from_string(f'{tmp} {op} {rhs}'))

        # objective
        mode = 'min' if self.model.objective.root.mode == 'max' else 'max'
        newvar = self.names['objective' if self.convert_from_dual else 'dual_objective']
        tmp = primal_coefs[0]['']
        for i,k in enumerate(variables):
            tmp = BinaryOp('+', tmp, BinaryOp('*', primal_coefs[i+1][''], k))
        dual_model.objective = ObjectiveTree.from_string(f'{mode} {newvar} = {tmp}')
        dual_model.variables = [newvar, *primal_variables]

        # finish
        self.model = dual_model
        self.do_normalize(rename=False)
        self.initial_variables = self.model.variables[:]

    def do_canonical(self):
        self.do_normalize(rename=False) # just in case

        # rewrite
        self.rewriter.do_canonical(self.model.objective)
        for c in self.model.constraints:
            self.rewriter.do_canonical(c)

        # split new "and" constraints
        tmp = []
        tmpstr = []
        for c in self.model.constraints:
            self._cut_and_add(c, tmp, tmpstr)
        self.model.constraints = tmp

        # rename single-variable constraints
        newvar = self.names['dual_variable' if self.convert_to_dual else 'variable']
        for oldvar in self.model.variables[:]:
            varid = 1
            if oldvar == self.names['dual_objective' if self.convert_to_dual else 'objective']:
                continue
            varmin = None
            varmax = None
            in_prog = oldvar in self.model.objective.variables
            for c in self.model.constraints:
                if oldvar not in c.variables:
                    continue
                if c.variables != [oldvar]:
                    in_prog = True
                    continue
                eleft = c.root.left.left if isinstance(c.root.left, BinaryOp) else Literal(1)
                eright = c.root.right
                vleft = eleft.evaluate({})
                vright = eright.evaluate({})
                if (c.root.op == '>=' and vleft > 0) or (c.root.op == '<=' and vleft < 0):
                    if not varmin or varmin.evaluate({}) < vright/vleft:
                        varmin = self.rewriter.normalize_tree(BinaryOp('/', eright, eleft))
                else:
                    if not varmax or varmax.evaluate({}) > vright/vleft:
                        varmax = self.rewriter.normalize_tree(BinaryOp('/', eright, eleft))
            if not in_prog:
                print(self.formatter.format_info(f'problem: {oldvar} is unused'))
                self.model.variables.remove(oldvar)
                if oldvar in self.model.variables:
                    self.model.variables.remove(oldvar)
                if oldvar in self.initial_variables:
                    self.initial_variables.remove(oldvar)
                for v in self.renames.values():
                    v.replace(oldvar, Literal(0))
                if oldvar in self.renames:
                    del self.renames[oldvar]
                print(self.formatter.format_decision('removing associated constraints'))
                self.model.constraints = [c for c in self.model.constraints if oldvar not in c.variables]
                continue
            # for debug: varmin <= oldvar <= varmax
            def to_expr(s):
                return MathTree.from_string(str(s)).root
            if varmin is None:
                if varmax is None:
                    print(self.formatter.format_info(f'problem: {oldvar} is free'))
                    while f'{newvar}{varid}' in self.model.variables:
                        varid += 1
                    _varid = varid
                    varid += 1
                    while f'{newvar}{varid}' in self.model.variables:
                        varid += 1
                    newexpr = to_expr(f'{newvar}{_varid} - {newvar}{varid}')
                    if oldvar in self.initial_variables:
                        self.renames[oldvar] = MathTree(newexpr)
                    else:
                        for v in self.renames.values():
                            v.replace(Variable(oldvar), newexpr)
                    if oldvar in self.model.objective.variables:
                        self.model.objective.replace(Variable(oldvar), newexpr)
                    for c in self.model.constraints:
                        if oldvar in c.variables:
                            c.replace(Variable(oldvar), newexpr)
                    self.model.variables.append(f'{newvar}{_varid}')
                    self.model.variables.append(f'{newvar}{varid}')
                    self.model.constraints.append(BoolTree.from_string(f'{newvar}{_varid} >= 0'))
                    self.model.constraints.append(BoolTree.from_string(f'{newvar}{varid} >= 0'))
                    print(self.formatter.format_decision(f'introduced {newvar}{_varid} and {newvar}{varid} >= 0 such that {oldvar} = {newexpr})'))
                elif varmax.evaluate({}) == 0:
                    print(self.formatter.format_info(f'problem: {oldvar} <= {varmax}'))
                    while f'{newvar}{varid}' in self.model.variables:
                        varid += 1
                    newexpr = to_expr(f'-{newvar}{varid}')
                    newexpr2 = to_expr(f'-{oldvar}')
                    if oldvar in self.initial_variables:
                        self.renames[oldvar] = MathTree(newexpr)
                    else:
                        for v in self.renames.values():
                            v.replace(Variable(oldvar), newexpr)
                    if oldvar in self.model.objective.variables:
                        self.model.objective.replace(Variable(oldvar), newexpr)
                    for c in self.model.constraints:
                        if oldvar in c.variables:
                            c.replace(Variable(oldvar), newexpr)
                    self.model.variables.append(f'{newvar}{varid}')
                    print(self.formatter.format_decision(f'introduced {newvar}{varid} = {newexpr2} >= 0 (i.e., {oldvar} = {newexpr})'))
                elif varmax.evaluate({}) > 0:
                    print(self.formatter.format_info(f'problem: {oldvar} <= {varmax}'))
                    while f'{newvar}{varid}' in self.model.variables:
                        varid += 1
                    newexpr = to_expr(f'-{newvar}{varid} + {varmax}')
                    newexpr2 = to_expr(f'{varmax} - {oldvar}')
                    if oldvar in self.initial_variables:
                        self.renames[oldvar] = MathTree(newexpr)
                    else:
                        for v in self.renames.values():
                            v.replace(Variable(oldvar), newexpr)
                    if oldvar in self.model.objective.variables:
                        self.model.objective.replace(Variable(oldvar), newexpr)
                    for c in self.model.constraints:
                        if oldvar in c.variables:
                            c.replace(Variable(oldvar), newexpr)
                    self.model.variables.append(f'{newvar}{varid}')
                    print(self.formatter.format_decision(f'introduced {newvar}{varid} = {newexpr2} >= 0 (i.e., {oldvar} = {newexpr})'))
                else:
                    print(self.formatter.format_info(f'problem: {oldvar} <= {varmax}'))
                    while f'{newvar}{varid}' in self.model.variables:
                        varid += 1
                    tmp = self.rewriter.normalize_tree(UnaryOp('-', varmax))
                    newexpr = to_expr(f'-{newvar}{varid} - {tmp}')
                    newexpr2 = to_expr(f'-{oldvar} - {tmp}')
                    if oldvar in self.initial_variables:
                        self.renames[oldvar] = MathTree(newexpr)
                    else:
                        for v in self.renames.values():
                            v.replace(Variable(oldvar), newexpr)
                    if oldvar in self.model.objective.variables:
                        self.model.objective.replace(Variable(oldvar), newexpr)
                    for c in self.model.constraints:
                        if oldvar in c.variables:
                            c.replace(Variable(oldvar), newexpr)
                    self.model.variables.append(f'{newvar}{varid}')
                    print(self.formatter.format_decision(f'introduced {newvar}{varid} = {newexpr2} >= 0 (i.e., {oldvar} = {newexpr})'))
            elif varmin and varmax and varmin.evaluate({}) == varmax.evaluate({}):
                print(self.formatter.format_info(f'problem: {oldvar} == {varmin}'))
                newexpr = varmin
                if oldvar in self.model.objective.variables:
                    self.model.objective.replace(Variable(oldvar), newexpr)
                for c in self.model.constraints:
                    if oldvar in c.variables:
                        c.replace(Variable(oldvar), newexpr)
                        self.rewriter.normalize(c)
                self.summary['eliminated'][oldvar] = newexpr
                print(self.formatter.format_decision(f'eliminated {oldvar} everywhere'))
            elif varmax and varmin.evaluate({}) > varmax.evaluate({}):
                print(self.formatter.format_decision(f'infeasible ({oldvar} <= {varmax} and {oldvar} >= {varmin})'))
                self.summary['status'] = 'INFEASIBLE'
                return
            elif varmin.evaluate({}) > 0:
                if varmax:
                    print(self.formatter.format_info(f'problem: {varmin} <= {oldvar} <= {varmax}'))
                else:
                    print(self.formatter.format_info(f'problem: {varmin} <= {oldvar}'))
                while f'{newvar}{varid}' in self.model.variables:
                    varid += 1
                newexpr = to_expr(f'{newvar}{varid} + {varmin}')
                newexpr2 = to_expr(f'{oldvar} - {varmin}')
                if oldvar in self.initial_variables:
                    self.renames[oldvar] = MathTree(newexpr)
                else:
                    for v in self.renames.values():
                        v.replace(Variable(oldvar), newexpr)
                if oldvar in self.model.objective.variables:
                    self.model.objective.replace(Variable(oldvar), newexpr)
                for c in self.model.constraints:
                    if oldvar in c.variables:
                        c.replace(Variable(oldvar), newexpr)
                self.model.variables.append(f'{newvar}{varid}')
                print(self.formatter.format_decision(f'introduced {newvar}{varid} = {newexpr2} >= 0 (i.e., {oldvar} = {newexpr})'))
            elif varmin.evaluate({}) < 0:
                if varmax:
                    print(self.formatter.format_info(f'problem: {varmin} <= {oldvar} <= {varmax}'))
                else:
                    print(self.formatter.format_info(f'problem: {varmin} <= {oldvar}'))
                while f'{newvar}{varid}' in self.model.variables:
                    varid += 1
                tmp = self.rewriter.normalize_tree(UnaryOp('-', varmin))
                newexpr = to_expr(f'{newvar}{varid} - {tmp}')
                newexpr2 = to_expr(f'{oldvar} + {tmp}')
                if oldvar in self.initial_variables:
                    self.renames[oldvar] = MathTree(newexpr)
                else:
                    for v in self.renames.values():
                        v.replace(Variable(oldvar), newexpr)
                if oldvar in self.model.objective.variables:
                    self.model.objective.replace(Variable(oldvar), newexpr)
                for c in self.model.constraints:
                    if oldvar in c.variables:
                        c.replace(Variable(oldvar), newexpr)
                self.model.variables.append(f'{newvar}{varid}')
                print(self.formatter.format_decision(f'introduced {newvar}{varid} = {newexpr2} >= 0 (i.e., {oldvar} = {newexpr})'))

        self.model.objective.variables = prefix_sort(self.model.objective.variables)
        self.rewriter.do_canonical(self.model.objective)
        for c in self.model.constraints:
            self.rewriter.do_canonical(c)

    def do_standard(self):
        self.do_canonical()
        # introduce slack variables
        self.initial_basis = []
        self.artificial_variables = []
        for c in self.model.constraints[:]:
            newvar = self.names['slack']
            if not (isinstance(c.root.left, Variable) and isinstance(c.root.right, Literal) and c.root.right.value == 0):
                varid = 1
                while f'{newvar}{varid}' in self.model.variables:
                    varid += 1
                sign = '+' if c.root.op == '<=' else '-'
                c.root = BinaryOp('==', BinaryOp(sign, c.root.left, Variable(f'{newvar}{varid}')), c.root.right)
                c.variables.append(f'{newvar}{varid}')
                self.rewriter.normalize(c)
                self.model.variables.append(f'{newvar}{varid}')
                self.model.constraints.append(BoolTree(BinaryOp('>=', Variable(f'{newvar}{varid}'), Literal(0))))
                # introduce artificial variables
                if c.root.right.evaluate({}) < 0:
                    print(self.formatter.format_info('problem: negative right-hand side'))
                    newvar = self.names['artificial']
                    varid = 1
                    while f'{newvar}{varid}' in self.model.variables:
                        varid += 1
                    c.root = BinaryOp('==', BinaryOp('+', UnaryOp('-', c.root.left), Variable(f'{newvar}{varid}')), UnaryOp('-', c.root.right))
                    c.variables.append(f'{newvar}{varid}')
                    self.model.constraints.append(BoolTree(BinaryOp('>=', Variable(f'{newvar}{varid}'), Literal(0))))
                    self.model.variables.append(f'{newvar}{varid}')
                    self.artificial_variables.append(f'{newvar}{varid}')
                    print(self.formatter.format_decision(f'introduced artificial variable {newvar}{varid} >= 0'))
                self.initial_basis.append(f'{newvar}{varid}')
        self.model.objective.variables = prefix_sort(self.model.objective.variables)
        self.rewriter.normalize(self.model.objective)
        for c in self.model.constraints:
            self.rewriter.normalize(c)

    def do_trivial_check(self):
        self.do_trivial_logic_check()
        self.do_trivial_constraint_check()

    def do_trivial_logic_check(self):
        # fail on "False"
        if any(str(c) == 'False' for c in self.model.constraints):
            print(self.formatter.format_decision('infeasible (there are trivially False constraints)'))
            self.summary['status'] = 'INFEASIBLE'
            return
        # remove "True"
        self.model.constraints = [c for c in self.model.constraints if str(c) != 'True']

    def do_trivial_constraint_check(self):
        # fail on weird constraints
        for c in self.model.constraints:
            if not isinstance(c.root, BinaryOp) and c.root in ['<=', '>=']:
                msg = f'Illegal constraint: {c}'
                raise RuntimeError(msg)
        # reorder "<=" before ">="
        if not [c for c in self.model.constraints if c.root.op == '<=']:
            print(self.formatter.format_info('problem: there is no (<=) constraint'))
            self.do_trivial_final()
            return

    def do_trivial_final(self):
        if self.summary['status'] == 'INFEASIBLE':
            return
        tab = Tableau(self.model.objective, self.model.constraints, [])
        coefs_exprs = tab.coefs_obj(self.model.objective.variables)
        coefs_values = {k: -v.evaluate({}) for k,v in coefs_exprs.items()}
        context = {}
        inf = float('inf')
        for k, v in coefs_values.items():
            if v > 0:
                context[k] = inf if self.model.objective.root.mode == 'max' else 0
            elif v < 0:
                context[k] = inf if self.model.objective.root.mode == 'min' else 0
        if abs(self.model.objective.evaluate(context)) == inf:
            self.summary['status'] = 'UNBOUNDED'
        else:
            self.summary['status'] = 'SOLVED'

        # final values
        exprs = {v: Literal(0) for v in self.model.variables}
        tmp_e = MathTree(self.model.objective.root.left)
        self.rewriter.normalize(tmp_e)
        if isinstance(tmp_e.root, Variable):
            obj_v = tmp_e.root.name
            exprs[obj_v] = Literal(self.model.objective.evaluate(context))
        else:
            assert isinstance(tmp_e.root.right, Variable)
            obj_v = tmp_e.root.right.name
            exprs[obj_v] = Literal(-self.model.objective.evaluate(context))

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

    def do_simplex_step(self):
        print(self.formatter.format_step('Simplex step'))

        # sanity check
        for line in self.tableau.data[1:]:
            if line[''].evaluate({}) < 0:
                msg = 'negative RHS for basic variable?!'
                raise RuntimeError(msg)

        # first, look for the entering variable
        print(self.formatter.format_action('Searching for a variable to enter the basis'))
        candidates = [k for k in self.tableau.variables if k not in self.tableau.basis]
        coefs_exprs = self.tableau.coefs_obj(candidates)
        if self.formatter.opposite_obj:
            coefs_exprs = {k: Rewriter().normalize_tree(UnaryOp('-', v)) for k,v in coefs_exprs.items()}
        coefs_values = {k: coefs_exprs[k].evaluate({}) for k in candidates}
        tmp = 'coefficients in objective row:'
        for k in candidates:
            e = coefs_exprs[k]
            v = coefs_values[k]
            tmp += f' {k}: {e}'
            if str(e) != str(v):
                tmp += f'={round(coefs_values[k], 8)}'
            tmp += ' ;'
        print(self.formatter.format_info(tmp[:-2]))
        if self.formatter.opposite_obj:
            candidates = [v for v in candidates if coefs_values[v] > 0]
        else:
            candidates = [v for v in candidates if coefs_values[v] < 0]
        if not candidates:
            if self.formatter.opposite_obj:
                print(self.formatter.format_decision('finished (no strictly positive coefficient)'))
            else:
                print(self.formatter.format_decision('finished (no strictly negative coefficient)'))
            self.summary['status'] = 'SOLVED'
            return
        if len(candidates) == 1:
            var_in = candidates[0]
            if self.formatter.opposite_obj:
                print(self.formatter.format_decision(f'selected {var_in} (only positive coefficient)'))
            else:
                print(self.formatter.format_decision(f'selected {var_in} (only negative coefficient)'))
        elif self.formatter.opposite_obj:
            var_in = max(candidates, key=lambda v: coefs_values[v])
            print(self.formatter.format_decision(f'selected {var_in} (max positive coefficient)'))
        else:
            var_in = min(candidates, key=lambda v: coefs_values[v])
            print(self.formatter.format_decision(f'selecting {var_in} (min negative coefficient)'))

        # then, look for the exiting variable
        print(self.formatter.format_action('Searching for a variable to exit the basis'))
        candidates = self.tableau.basis[:]
        col_lit = self.tableau.coefs_column('')
        col_var = self.tableau.coefs_column(var_in)
        coefs_exprs = {k: col_var[k] for k in candidates}
        coefs_values = {k: coefs_exprs[k].evaluate({}) for k in candidates}
        tmp = f'coefficients in {var_in} column:'
        for k in candidates:
            e = coefs_exprs[k]
            v = coefs_values[k]
            tmp += f' {k}: {e}'
            if str(e) != str(v):
                tmp += f'={round(coefs_values[k], 8)}'
            tmp += ' ;'
        print(self.formatter.format_info(tmp[:-2]))
        candidates = [k for k in candidates if coefs_values[k] > 0]
        if not candidates:
            print(self.formatter.format_decision('aborted: unbounded program (none strictly positive)'))
            self.summary['status'] = 'UNBOUNDED'
            return
        if len(candidates) < len(self.tableau.basis):
            print(self.formatter.format_decision('discarded any variable without a positive coefficient'))
        coefs_exprs = {k: Rewriter().normalize_tree(BinaryOp('/', col_lit[k], col_var[k])) for k in candidates}
        coefs_values = {k: coefs_exprs[k].evaluate({}) for k in candidates}
        tmp = 'ratios:'
        for k in candidates:
            e = coefs_exprs[k]
            v = coefs_values[k]
            tmp += f' {k}: {e}'
            if str(e) != str(v):
                tmp += f'={round(coefs_values[k], 8)}'
            tmp += ' ;'
        print(self.formatter.format_info(tmp[:-2]))
        candidates = [k for k in candidates if coefs_values[k] >= 0]
        if not candidates:
            print(self.formatter.format_decision('unbounded (no strictly positive ratio)'))
            self.summary['status'] = 'UNBOUNDED'
            return
        if len(candidates) == 1:
            var_out = candidates[0]
            print(self.formatter.format_decision(f'selected {var_out} (only positive ratio)'))
        else:
            var_out = min(candidates, key=lambda k: coefs_values[k])
            print(self.formatter.format_decision(f'selected {var_out} (min positive ratio)'))

        # finally, pivot
        print(self.formatter.format_action(f'Pivoting on ({var_in}, {var_out})'))
        self.tableau.pivot(var_in, var_out)

    def do_simplex_final(self):
        # final values
        exprs = {v: Literal(0) for v in self.model.variables}
        for k, v in self.summary['eliminated'].items():
            exprs[k] = Literal(v)
        for k in self.tableau.basis:
            row = self.tableau.coefs_row(k)
            exprs[k] = row['']
        tmp_e = MathTree(self.model.objective.root.left)
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
            if self.model.objective.root.mode == 'max':
                self.summary['values'][obj_v] = '-inf' if isinstance(self.model.objective.root.left, UnaryOp) else 'inf'
            elif self.model.objective.root.mode == 'min':
                self.summary['values'][obj_v] = 'inf' if isinstance(self.model.objective.root.left, UnaryOp) else '-inf'

        if self.summary['status'] == 'SOLVED':
            self.summary['objective'] = str(exprs[obj_v])
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
