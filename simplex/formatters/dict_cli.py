from .cli import AbstractCliFormatter

from simplex.core import Rewriter
from simplex.parsing import UnaryOp, MathTree


class DictCliFormatter(AbstractCliFormatter):
    def format_tableau(self, tableau):
        out = []
        # sizes for alignment
        head_just = max(*(len(v) for v in tableau.basis), len(str(tableau.objective.root.var)))
        just = {v: 0 for v in tableau.columns}
        for line in tableau.data:
            for v in tableau.columns:
                t = MathTree(UnaryOp('-', line[v]))
                Rewriter().normalize(t)
                just[v] = max(just[v], len(str(t)), len(str(line[v])))
        for v in tableau.columns:
            just[v] += len(v) + (1 if v else 0)
        # objective
        tmp = []
        tmp.append(str(tableau.objective.root.var).rjust(head_just))
        tmp.append(' = ')
        line = tableau.data[0]
        for k, v in enumerate(tableau.dict_columns):
            if v in tableau.basis and str(line[v]) == '0':
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
        for b in tableau.basis:
            line = tableau.row_for_basic(b)
            tmp = []
            tmp.append(str(b.rjust(head_just)))
            tmp.append(' = ')
            for k, v in enumerate(tableau.dict_columns):
                if v in tableau.basis and str(tableau.data[0][v]) == '0':
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
