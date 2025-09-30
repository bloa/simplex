from .cli import AbstractCliFormatter

from simplex.core import Rewriter
from simplex.parsing import UnaryOp, MathTree


class TableauCliFormatter(AbstractCliFormatter):
    def __init__(self):
        self.compact = False
        self.opposite_obj = True

    def format_tableau(self, tableau):
        out = []
        # sizes for alignment
        head_just = max(*(len(v) for v in tableau.basis), len(str(tableau.objective.root.left)))
        just = {v: len(v) for v in tableau.columns}
        for line in tableau.data:
            for v in tableau.columns:
                e = MathTree(UnaryOp('-', line[v]))
                Rewriter().normalize(e)
                just[v] = max(just[v], len(str(e)), len(str(line[v])))
        # header
        tmp = []
        sep = []
        for k, v in enumerate(tableau.columns):
            if self.compact and v in tableau.basis:
                continue
            if k > 0:
                tmp.append('  ' if v else ' | ')
                sep.append('--' if v else '-+-')
            tmp.append(v.rjust(just[v]))
            sep.append('-'*len(tmp[-1]))
        tmp.append('   ' + ' '*head_just)
        sep.append('-=-' + '-'*head_just)
        out.append(''.join(tmp))
        out.append(''.join(sep))
        # data
        for j, line in enumerate(tableau.data):
            # alt: objective on top
            if self.opposite_obj and j == 0:
                continue
            tmp = []
            for k, v in enumerate(line):
                if self.compact and v in tableau.basis:
                    continue
                if k > 0:
                    tmp.append('  ' if v else ' | ')
                tmp.append(str(line[v]).rjust(just[v]))
            tmp.append(' = ')
            e = tableau.objective.root.left if j == 0 else tableau.basis[j-1]
            tmp.append(str(e).rjust(head_just))
            out.append(''.join(tmp))
        # alt: objective on top
        if self.opposite_obj:
            out.append(''.join(sep))
            line = tableau.data[0]
            tmp = []
            for k, v in enumerate(line):
                if self.compact and v in tableau.basis:
                    continue
                if k > 0:
                    tmp.append('  ' if v else ' | ')
                e = MathTree(UnaryOp('-', line[v]))
                Rewriter().normalize(e)
                tmp.append(str(e).rjust(just[v]))
            tmp.append(' = ')
            e = MathTree(UnaryOp('-', tableau.objective.root.left))
            Rewriter().normalize(e)
            tmp.append(str(e).rjust(head_just))
            out.append(''.join(tmp))

        return self.indent(out)
