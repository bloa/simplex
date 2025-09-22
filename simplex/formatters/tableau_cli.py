from .cli import AbstractCliFormatter


class TableauCliFormatter(AbstractCliFormatter):
    def __init__(self):
        self.compact = False

    def format_tableau(self, tableau):
        out = []
        head_just = max(*(len(v) for v in tableau.basis), len(str(tableau.objective.root.var)))
        just = {v: len(v) for v in tableau.columns}
        for line in tableau.data:
            for v in tableau.columns:
                just[v] = max(just[v], len(str(line[v])))
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
        for j, line in enumerate(tableau.data):
            tmp = []
            for k, v in enumerate(line):
                if self.compact and v in tableau.basis:
                    continue
                if k > 0:
                    tmp.append('  ' if v else ' | ')
                tmp.append(str(line[v]).rjust(just[v]))
            tmp.append(' = ')
            e = tableau.objective.root.var if j == 0 else tableau.basis[j-1]
            tmp.append(str(e).rjust(head_just))
            out.append(''.join(tmp))
        return '\n'.join(out)
