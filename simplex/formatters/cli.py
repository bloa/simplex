from simplex.core import AbstractFormatter
from simplex.parsing import BinaryOp, ExprList, Literal, Variable
from simplex.utils import prefix_sort


class AbstractCliFormatter(AbstractFormatter):
    @staticmethod
    def bold(text):
        return f'\033[1m{text}\033[0m'

    @staticmethod
    def indent(lines):
        out = [f'    {line}' for line in lines]
        return '\n'.join(out)

    def format_section(self, title):
        out = []
        out.append(self.bold(f'# {title}'))
        out.append(self.bold('-----------------------------------'))
        return '\n'.join(out)

    def format_step(self, title):
        return self.bold(f'* {title}')

    def format_raw_model(self, raw):
        out = [line for line in raw.split('\n') if line.strip()]
        return self.indent(out)

    def format_model(self, model):
        out = [str(model.objective)]
        neg_var = []
        pos_var = []
        for c in model.constraints:
            e = c.root
            if isinstance(e, BinaryOp) and isinstance(e.left, Variable) and isinstance(e.right, Literal) and e.right.value == 0:
                if e.op == '<=':
                    neg_var.append(e.left.name)
                elif e.op == '>=':
                    pos_var.append(e.left.name)
            else:
                out.append(str(e))
        if neg_var:
            out.append(str(BinaryOp('<=', ExprList(prefix_sort(neg_var)), Literal(0))))
        if pos_var:
            out.append(str(BinaryOp('>=', ExprList(prefix_sort(pos_var)), Literal(0))))
        return self.indent(out)
