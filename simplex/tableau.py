from .expr_nodes import BinaryOp, Literal, UnaryOp, Variable
from .expr_tree import MathTree
from .rewriter import Rewriter
from .utils import prefix_unique

class Tableau:
    def __init__(self, objective, constraints, basis):
        tmp = objective.variables
        obj_e = objective.root.var
        while True:
            if isinstance(obj_e, Variable):
                break
            obj_e = obj_e.right
        tmp.remove(obj_e.name)
        for c in constraints:
            tmp += c.variables
        self.variables = prefix_unique(tmp)
        self.objective = objective
        self.constraints = constraints
        self.columns = [*self.variables, '']
        self.dict_columns = ['', *self.variables]
        self.data = []
        tmp = {}
        for k, v in self.aux_data(self.objective.root.right, self.columns).items():
            t = MathTree(UnaryOp('-', v) if k else v)
            Rewriter().normalize(t)
            tmp[k] = t.root
        self.data.append(tmp)
        for c in self.constraints:
            if c.root.op == '==':
                tmp = self.aux_data(c.root.left, self.columns)
                for k, v in self.aux_data(c.root.right, self.columns).items():
                    tmp[k] = BinaryOp('-', tmp[k], v)
                for k, v in tmp.items():
                    t = MathTree(v if k else UnaryOp('-', v))
                    Rewriter().normalize(t)
                    tmp[k] = t.root
                self.data.append(tmp)
        self.basis = basis
        assert len(basis) == len([c for c in constraints if c.root.op == '=='])

    def delete(self, oldvar):
        assert oldvar in self.variables
        assert oldvar not in self.basis
        self.variables.remove(oldvar)
        self.columns.remove(oldvar)
        self.dict_columns.remove(oldvar)
        for line in self.data:
            del line[oldvar]

    @staticmethod
    def aux_data(tree, columns):
        acc = {v: Literal(0) for v in columns}
        def visitor(node):
            nonlocal acc
            if isinstance(node, BinaryOp) and node.op == '*':
                acc[node.right.name] = node.left
                acc[''] = Literal(0)
            if isinstance(node, Variable):
                acc[node.name] = Literal(1)
            if isinstance(node, Literal):
                acc[''] = node
        tree.visit(visitor)
        for k, v in acc.items():
            tmp = MathTree(v)
            Rewriter().normalize(tmp)
            acc[k] = tmp.root
        return dict(acc)

    def coefs_obj(self, candidates):
        return {k: self.data[0][k].evaluate({}) for k in candidates}

    def coefs_obj_neg(self, candidates):
        return {k: -self.data[0][k].evaluate({}) for k in candidates}

    def coefs_column(self, col):
        return {v: self.data[k+1][col].evaluate({}) for k, v in enumerate(self.basis)}

    def row_for_basic(self, var):
        assert var in self.basis
        for row in self.data[1:]:
            if row[var].evaluate({}) == 1:
                return row
        raise RuntimeError

    def aux_art_candidates(self, taboo):
        return [v for v in self.variables if v not in self.basis and v not in taboo]

    @staticmethod
    def aux_art_coefs(row_out, candidates):
        num = row_out[''].evaluate({})
        def coef(v):
            denum = row_out[v].evaluate({})
            return float('-inf') if denum == 0 else num/denum
        return {v: coef(v) for v in candidates}

    def pivot(self, var_in, var_out):
        assert var_out in self.basis
        assert var_in not in self.basis

        # find pivot line
        for i, line_out in enumerate(self.data):
            if i == 0:
                continue
            if line_out[var_out].evaluate({}) == 1:
                break

        # find pivot coef
        coef = line_out[var_in]
        assert coef.evaluate({}) != 0

        # normalize pivot line
        for v in self.columns:
            line_out[v] = BinaryOp('/', line_out[v], coef)

        # update all other lines
        for j, line in enumerate(self.data):
            if j == i:
                continue
            coef = line[var_in]
            for v in self.columns:
                line[v] = BinaryOp('-', line[v], BinaryOp('*', coef, line_out[v]))

        # simplify expressions
        for line in self.data:
            for v in self.columns:
                expr = MathTree(line[v])
                Rewriter().normalize(expr)
                line[v] = expr.root

        # update basis and columns
        self.basis[self.basis.index(var_out)] = var_in
        tmp = self.dict_columns.index(var_in)
        self.dict_columns[self.dict_columns.index(var_out)] = var_in
        self.dict_columns[tmp] = var_out

    def to_tab(self):
        out = []
        head_just = max(*(len(v) for v in self.basis), len(str(self.objective.root.var)))
        just = {v: len(v) for v in self.columns}
        for line in self.data:
            for v in self.columns:
                just[v] = max(just[v], len(str(line[v])))
        tmp = []
        sep = []
        for k, v in enumerate(self.columns):
            if k > 0:
                tmp.append('  ' if v else ' | ')
                sep.append('--' if v else '-+-')
            tmp.append(v.rjust(just[v]))
            sep.append('-'*len(tmp[-1]))
        tmp.append('   ' + ' '*head_just)
        sep.append('-=-' + '-'*head_just)
        out.append(''.join(tmp))
        out.append(''.join(sep))
        for j, line in enumerate(self.data):
            tmp = []
            for k, v in enumerate(line):
                if k > 0:
                    tmp.append('  ' if v else ' | ')
                tmp.append(str(line[v]).rjust(just[v]))
            tmp.append(' = ')
            e = self.objective.root.var if j == 0 else self.basis[j-1]
            tmp.append(str(e).rjust(head_just))
            out.append(''.join(tmp))
        return '\n'.join(out)

    def to_dict(self):
        out = []
        # sizes for alignment
        head_just = max(*(len(v) for v in self.basis), len(str(self.objective.root.var)))
        just = {v: 0 for v in self.columns}
        for line in self.data:
            for v in self.columns:
                t = MathTree(UnaryOp('-', line[v]))
                Rewriter().normalize(t)
                just[v] = max(just[v], len(str(t)), len(str(line[v])))
        for v in self.columns:
            just[v] += len(v) + (1 if v else 0)
        # objective
        tmp = []
        tmp.append(str(self.objective.root.var).rjust(head_just))
        tmp.append(' = ')
        line = self.data[0]
        for k, v in enumerate(self.dict_columns):
            if v in self.basis and str(line[v]) == '0':
                continue
            expr = MathTree(UnaryOp('-', line[v]) if v else line[v])
            Rewriter().normalize(expr)
            x = expr.evaluate({})
            s = ''
            if v == '':
                s = str(expr)
            elif x != 0:
                if k > 0:
                    tmp.append(' + ')
                s = f'{expr}*{v}'
            elif k > 0:
                tmp.append('   ')
            tmp.append(s.rjust(just[v]))
        out.append(''.join(tmp))
        # constraints
        for b in self.basis:
            line = self.row_for_basic(b)
            tmp = []
            tmp.append(str(b.rjust(head_just)))
            tmp.append(' = ')
            for k, v in enumerate(self.dict_columns):
                if v in self.basis and str(self.data[0][v]) == '0':
                    continue
                expr = MathTree(UnaryOp('-', line[v]) if v else line[v])
                Rewriter().normalize(expr)
                x = expr.evaluate({})
                s = ''
                if v == '':
                    s = str(expr)
                elif v != b and x != 0:
                    if k > 0:
                        tmp.append(' + ')
                    s = f'{expr}*{v}'
                elif k > 0:
                    tmp.append('   ')
                tmp.append(s.rjust(just[v]))
            out.append(''.join(tmp))
        return '\n'.join(out)
