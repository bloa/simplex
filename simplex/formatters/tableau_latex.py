from .latex import AbstractLatexFormatter

from simplex.core import Rewriter
from simplex.parsing import UnaryOp, MathTree


class TableauLatexFormatter(AbstractLatexFormatter):
    def __init__(self):
        self.compact = False

    def format_tableau(self, tableau):
        out = []
        out.append(r'\begin{equation*}')
        n = len(tableau.columns)-len(tableau.basis) if self.compact else len(tableau.columns)
        out.append(r'  \begin{array}{' + 'r'*(n-1) + '|rcr}')
        # sizes for alignment
        head_just = max(*(len(v) for v in tableau.basis), len(str(tableau.objective.root.var)))
        just = {v: 0 for v in tableau.columns}
        for line in tableau.data:
            for v in tableau.columns:
                t = MathTree(UnaryOp('-', line[v]))
                Rewriter().normalize(t)
                just[v] = max(just[v], len(str(t)), len(str(line[v])))
        # header
        tmp = []
        for k, v in enumerate(tableau.columns):
            if self.compact and v in tableau.basis:
                continue
            if v:
                tmp.append(v.rjust(just[v]))
        out.append('    ' + ' & '.join(tmp) + r'\\')
        out.append(r'    \hline')
        # data
        for j, line in enumerate(tableau.data):
            tmp = []
            for k, v in enumerate(line):
                if self.compact and v in tableau.basis:
                    continue
                tmp.append(self.math_to_latex(line[v]).rjust(just[v]))
            tmp.append('=')
            e = tableau.objective.root.var if j == 0 else tableau.basis[j-1]
            tmp.append(self.math_to_latex(e).rjust(head_just))
            out.append('    ' + ' & '.join(tmp) + r'\\')
            if j == 0:
                out.append(r'    \hline')
        out.append(r'  \end{array}')
        out.append(r'\end{equation*}')
        return '\n'.join(out)
