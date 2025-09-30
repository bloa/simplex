from .latex import AbstractLatexFormatter

from simplex.core import Rewriter
from simplex.parsing import UnaryOp, MathTree


class DictLatexFormatter(AbstractLatexFormatter):
    def __init__(self):
        self.opposite_obj = True

    def format_tableau(self, tableau):
        out = []
        out.append(r'\begin{equation*}')
        out.append(r'  \begin{array}{|r' + 'cr'*(len(tableau.columns)-len(tableau.basis)) + '|}')
        out.append(r'    \hline')
        # sizes for alignment
        head_just = max(*(len(self.math_to_latex(v)) for v in tableau.basis), len(str(self.math_to_latex(tableau.objective.root.left))))
        just = {v: 0 for v in tableau.columns}
        for row in tableau.data:
            for v in tableau.columns:
                t = MathTree(UnaryOp('-', row[v]))
                Rewriter().normalize(t)
                just[v] = max(just[v], len(str(t)), len(str(row[v])))
        for v in tableau.columns:
            just[v] += len(v) + (1 if v else 0)
        # objective
        tmp = []
        tmp.append(str(tableau.objective.root.left).rjust(head_just))
        tmp.append('=')
        row = tableau.data[0]
        for k, v in enumerate(tableau.dict_columns):
            if v in tableau.basis and str(row[v]) == '0':
                continue
            expr = MathTree(UnaryOp('-', row[v]) if v else row[v])
            Rewriter().normalize(expr)
            x = expr.evaluate({})
            s = ''
            if v == '':
                s = self.math_to_latex(expr)
            elif x != 0:
                if k > 0:
                    tmp.append('+')
                s = self.math_to_latex(f'{expr}{v}')
            elif k > 0:
                tmp.append(' ')
            tmp.append(s.rjust(just[v]))
        out.append('    ' + ' & '.join(tmp) + r'\\')
        out.append(r'    \hline')
        # constraints
        for b in tableau.basis:
            row = tableau.coefs_row(b)
            tmp = []
            tmp.append(str(self.math_to_latex(b).rjust(head_just)))
            tmp.append('=')
            for k, v in enumerate(tableau.dict_columns):
                if v in tableau.basis and str(tableau.data[0][v]) == '0':
                    continue
                expr = MathTree(UnaryOp('-', row[v]) if v else row[v])
                Rewriter().normalize(expr)
                x = expr.evaluate({})
                s = ''
                if v == '':
                    s = self.math_to_latex(expr)
                elif v != b and x != 0:
                    if k > 0:
                        tmp.append('+')
                    s = self.math_to_latex(f'{expr}{v}')
                elif k > 0:
                    tmp.append(' ')
                tmp.append(s.rjust(just[v]))
            out.append('    ' + ' & '.join(tmp) + r'\\')
        out.append(r'    \hline')
        out.append(r'  \end{array}')
        out.append(r'\end{equation*}')
        return '\n'.join(out)
